"""
법제처 법령정보 API 서비스
.law-api/law_fetcher.py를 참조하여 작성
"""
import os
import re
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path

import httpx
from pydantic import BaseModel

from backend.core.config import settings


class LawData(BaseModel):
    """법령 데이터"""
    law_name: str
    law_id: str = ""
    proclaimed_date: str = ""
    enforced_date: str = ""
    ministry: str = ""
    articles: Dict[str, str] = {}
    raw_size: int = 0


class LawAPIService:
    """법제처 Open API 서비스 (캐싱 기능 포함)"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://www.law.go.kr/DRF/lawService.do",
        cache_dir: str = "./cache/laws",
        cache_expiry_days: int = 7,
    ):
        self.api_key = api_key or settings.MOLEG_API_KEY
        self.base_url = base_url
        self.cache_dir = Path(cache_dir)
        self.cache_expiry_days = cache_expiry_days
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_info_file = self.cache_dir / "cache_info.json"
        self.cache_info = self._load_cache_info()
        self.timeout = 30.0

    def _load_cache_info(self) -> Dict[str, Any]:
        try:
            if self.cache_info_file.exists():
                with open(self.cache_info_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _save_cache_info(self) -> None:
        try:
            with open(self.cache_info_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache_info, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _get_cache_filename(self, law_name: str) -> Path:
        safe_name = re.sub(r'[^\w\-_\.]', '_', law_name)
        return self.cache_dir / f"{safe_name}.json"

    def _is_cache_valid(self, law_name: str) -> bool:
        try:
            cache_file = self._get_cache_filename(law_name)
            if not cache_file.exists() or law_name not in self.cache_info:
                return False
            cached_time = datetime.fromisoformat(self.cache_info[law_name]['cached_at'])
            if datetime.now() > cached_time + timedelta(days=self.cache_expiry_days):
                return False
            if cache_file.stat().st_size < 1000:
                return False
            return True
        except Exception:
            return False

    def _load_from_cache(self, law_name: str) -> Optional[str]:
        try:
            cache_file = self._get_cache_filename(law_name)
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f).get('raw_data')
        except Exception:
            return None

    def _save_to_cache(self, law_name: str, raw_data: str) -> None:
        try:
            cache_file = self._get_cache_filename(law_name)
            cache_data = {
                'law_name': law_name,
                'raw_data': raw_data,
                'cached_at': datetime.now().isoformat(),
                'data_size': len(raw_data),
            }
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            self.cache_info[law_name] = {
                'cached_at': cache_data['cached_at'],
                'data_size': cache_data['data_size'],
            }
            self._save_cache_info()
        except Exception:
            pass

    def fetch_law_sync(self, law_name: str, use_cache: bool = True) -> Optional[str]:
        """단일 법령 조회 (동기 버전) - LM 파라미터로 법령명 직접 조회"""
        if use_cache and self._is_cache_valid(law_name):
            cached = self._load_from_cache(law_name)
            if cached:
                return cached

        try:
            params = {
                'OC': self.api_key,
                'target': 'law',
                'LM': law_name,
                'type': 'JSON',
            }
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(self.base_url, params=params)
                response.raise_for_status()
                if len(response.text) > 1000:
                    self._save_to_cache(law_name, response.text)
                    return response.text
        except Exception:
            fallback = self._load_from_cache(law_name)
            if fallback:
                return fallback
        return None

    async def fetch_law(self, law_name: str, use_cache: bool = True) -> Optional[str]:
        """단일 법령 조회 (비동기 버전) - LM 파라미터로 법령명 직접 조회"""
        if use_cache and self._is_cache_valid(law_name):
            cached = self._load_from_cache(law_name)
            if cached:
                return cached

        try:
            params = {
                'OC': self.api_key,
                'target': 'law',
                'LM': law_name,
                'type': 'JSON',
            }
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                if len(response.text) > 1000:
                    self._save_to_cache(law_name, response.text)
                    return response.text
        except Exception:
            fallback = self._load_from_cache(law_name)
            if fallback:
                return fallback
        return None

    def parse_law_response(self, json_content: str) -> Optional[LawData]:
        """JSON 응답 파싱"""
        try:
            data = json.loads(json_content)
            law_data = LawData(law_name="", raw_size=len(json_content))

            basic_info = data.get('법령', {}).get('기본정보') or data.get('기본정보')
            if basic_info:
                law_data.law_name = str(basic_info.get('법령명_한글', '')).strip()
                law_data.law_id = str(basic_info.get('법령ID', '')).strip()
                law_data.proclaimed_date = str(basic_info.get('공포일자', '')).strip()
                law_data.enforced_date = str(basic_info.get('시행일자', '')).strip()
                law_data.ministry = str(basic_info.get('소관부처', '')).strip()

            articles = {}
            article_units = data.get('법령', {}).get('조문', {}).get('조문단위', [])
            for unit in article_units:
                # 조문구분이 '조문'인 것만 처리
                article_type = unit.get('조문구분', '')
                article_num_str = unit.get('조문번호', '')

                if not article_num_str:
                    continue

                try:
                    article_num = int(article_num_str)
                    if article_num <= 0:
                        continue

                    branch_num = unit.get('조문가지번호', '')
                    base_key = f"{article_num}-{branch_num}" if branch_num else str(article_num)
                    article_key = f"{base_key}_조문"

                    full_content = self._build_article_content(unit, article_num, branch_num, article_type)
                    if full_content.strip():
                        articles[article_key] = full_content.strip()
                except (ValueError, TypeError):
                    continue

            law_data.articles = articles
            return law_data
        except Exception as e:
            print(f"Parse error: {e}")
            return None

    def _build_article_content(self, unit: Dict, article_num: int, branch_num: str, article_type: str) -> str:
        """조문 내용 구성"""
        # 조문제목에 실제 조문 내용이 들어있음
        article_title = unit.get('조문제목', '')
        article_content = unit.get('조문내용', '') or article_title

        if article_type == '전문':
            identifier = article_title or f'전문 {article_num}'
        else:
            identifier = f'제{article_num}조의{branch_num}' if branch_num else f'제{article_num}조'

        full = str(article_content) if article_content else identifier
        if article_title and f'({article_title})' not in full:
            full = f'{full}({article_title})'

        # 항 추가
        if '항' in unit and isinstance(unit['항'], list):
            for hang_item in unit['항']:
                if isinstance(hang_item, dict) and '항내용' in hang_item:
                    full += '\n' + str(hang_item['항내용'])

                    if '호' in hang_item and isinstance(hang_item['호'], list):
                        for ho_item in hang_item['호']:
                            if isinstance(ho_item, dict) and '호내용' in ho_item:
                                full += '\n' + str(ho_item['호내용'])

                                if '목' in ho_item and isinstance(ho_item['목'], list):
                                    for mok_item in ho_item['목']:
                                        if isinstance(mok_item, dict) and '목내용' in mok_item:
                                            full += '\n' + str(mok_item['목내용'])
        return full

    def fetch_and_parse_sync(self, law_name: str, use_cache: bool = True) -> Optional[LawData]:
        """법령 조회 및 파싱 (동기)"""
        raw = self.fetch_law_sync(law_name, use_cache)
        return self.parse_law_response(raw) if raw else None

    async def fetch_and_parse(self, law_name: str, use_cache: bool = True) -> Optional[LawData]:
        """법령 조회 및 파싱 (비동기)"""
        raw = await self.fetch_law(law_name, use_cache)
        return self.parse_law_response(raw) if raw else None

    def clear_cache(self, law_name: Optional[str] = None) -> None:
        """캐시 삭제"""
        import shutil
        try:
            if law_name:
                if law_name in self.cache_info:
                    cache_file = self._get_cache_filename(law_name)
                    if cache_file.exists():
                        cache_file.unlink()
                    del self.cache_info[law_name]
                    self._save_cache_info()
            else:
                if self.cache_dir.exists():
                    shutil.rmtree(self.cache_dir)
                    self.cache_dir.mkdir(parents=True, exist_ok=True)
                self.cache_info = {}
        except Exception:
            pass

    def get_cache_status(self) -> Dict[str, Any]:
        """캐시 상태 조회"""
        return {
            'cache_dir': str(self.cache_dir),
            'cached_laws': list(self.cache_info.keys()),
            'total_cached': len(self.cache_info),
        }
