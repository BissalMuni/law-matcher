"""
MOLEG (법제처) API Client
"""
import asyncio
import logging
import xml.etree.ElementTree as ET
from typing import Optional, List, Dict, Any
import httpx
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class LinkedOrdinance(BaseModel):
    """연계 조례 정보 (lnkOrg API)"""
    ordinance_id: str  # 자치법규ID
    ordinance_serial_no: str  # 자치법규일련번호
    ordinance_name: str  # 자치법규명
    ordinance_type: str  # 자치법규종류 (조례/규칙)
    law_id: str  # 상위법령ID
    law_name: str  # 상위법령명 (법령명한글)
    enacted_date: Optional[str] = None  # 공포일자
    enforced_date: Optional[str] = None  # 시행일자
    revision_type: Optional[str] = None  # 제개정구분명


class LawArticle(BaseModel):
    """Law article"""
    article_no: str
    article_title: Optional[str] = None
    article_content: str
    paragraphs: List[Dict[str, Any]] = Field(default_factory=list)
    revision_type_detail: Optional[str] = None  # 조문제개정유형: 신설/일부개정/전부개정
    change_flag: Optional[str] = None  # 조문변경여부: Y/N


class LawDetail(BaseModel):
    """Law detail"""
    law_id: str
    law_mst: str
    law_name: str
    law_type: str
    proclaimed_date: Optional[str] = None
    enforced_date: Optional[str] = None
    revision_type: Optional[str] = None
    revision_reason: Optional[str] = None  # 제개정이유내용
    amendment_content: Optional[str] = None  # 개정문내용
    articles: List[LawArticle] = Field(default_factory=list)


class OrdinanceDetail(BaseModel):
    """자치법규 본문 상세 (lawService.do?target=ordin)"""
    ordinance_id: str  # 자치법규ID
    serial_no: str  # 자치법규일련번호
    ordinance_name: str  # 자치법규명
    ordinance_type: Optional[str] = None  # 자치법규종류
    proclaimed_date: Optional[str] = None  # 공포일자
    enforced_date: Optional[str] = None  # 시행일자
    revision_reason: Optional[str] = None  # 제개정이유내용
    amendment_content: Optional[str] = None  # 개정문내용
    articles: List[LawArticle] = Field(default_factory=list)  # 조문 목록


class MolegClient:
    """MOLEG Open API client"""

    def __init__(self, api_key: str, base_url: str = "https://www.law.go.kr/DRF"):
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.max_retries = 2
        self.base_delay = 1.0  # 초기 대기시간 1초

    async def _request_with_retry(self, method: str, url: str, **kwargs) -> httpx.Response:
        """지수 백오프 재시도가 포함된 HTTP 요청"""
        last_exc = None
        for attempt in range(self.max_retries + 1):
            try:
                response = await self.client.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_exc = e
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt)
                    logger.warning("법제처 API 요청 실패 (시도 %d/%d), %s초 후 재시도: %s", attempt + 1, self.max_retries + 1, delay, str(e))
                    await asyncio.sleep(delay)
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500 and attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt)
                    logger.warning("법제처 API 서버 오류 %d (시도 %d/%d), %s초 후 재시도", e.response.status_code, attempt + 1, self.max_retries + 1, delay)
                    await asyncio.sleep(delay)
                    last_exc = e
                else:
                    raise
        raise last_exc  # type: ignore

    async def get_law_list(
        self,
        query: Optional[str] = None,
        law_type: Optional[str] = None,
        page: int = 1,
    ) -> List[Dict[str, Any]]:
        """Get law list"""
        params = {
            "OC": self.api_key,
            "target": "law",
            "type": "JSON",
            "page": page,
        }
        if query:
            params["query"] = query
        if law_type:
            params["lsClscd"] = law_type

        response = await self._request_with_retry(
            "GET",
            f"{self.base_url}/lawSearch.do",
            params=params,
        )

        data = response.json()
        return data.get("LawSearch", {}).get("law", [])

    async def get_law_detail(self, law_mst: str) -> LawDetail:
        """Get law detail by MST (JSON first, XML fallback)."""
        try:
            return await self._get_law_detail_json(law_mst)
        except Exception as json_error:
            logger.warning(
                "JSON law detail parsing failed for MST=%s, trying XML fallback: %s",
                law_mst,
                json_error,
            )
            try:
                return await self._get_law_detail_xml(law_mst)
            except Exception as xml_error:
                logger.error(
                    "XML fallback failed for MST=%s: %s",
                    law_mst,
                    xml_error,
                )
                raise

    async def _get_law_detail_json(self, law_mst: str) -> LawDetail:
        params = {
            "OC": self.api_key,
            "target": "law",
            "MST": law_mst,
            "type": "JSON",
        }

        response = await self._request_with_retry(
            "GET",
            f"{self.base_url}/lawService.do",
            params=params,
        )

        data = response.json()
        law_data = data.get("법령", {})
        basic_info = law_data.get("기본정보", {})
        law_type_raw = basic_info.get("법종구분", {})
        law_type = law_type_raw.get("content", "") if isinstance(law_type_raw, dict) else law_type_raw

        # 제개정이유/개정문 파싱
        revision_reason = self._parse_nested_text(
            law_data.get("제개정이유", {}).get("제개정이유내용")
        )
        amendment_content = self._parse_nested_text(
            law_data.get("개정문", {}).get("개정문내용")
        )

        return LawDetail(
            law_id=self._normalize_text(basic_info.get("법령ID", "")),
            law_mst=law_mst,
            law_name=self._normalize_text(basic_info.get("법령명_한글", "")),
            law_type=self._normalize_text(law_type),
            proclaimed_date=self._normalize_text(basic_info.get("공포일자")) or None,
            enforced_date=self._normalize_text(basic_info.get("시행일자")) or None,
            revision_type=self._normalize_text(basic_info.get("제개정구분")) or None,
            revision_reason=revision_reason,
            amendment_content=amendment_content,
            articles=self._parse_articles(law_data.get("조문", {}).get("조문단위", [])),
        )

    async def _get_law_detail_xml(self, law_mst: str) -> LawDetail:
        params = {
            "OC": self.api_key,
            "target": "law",
            "MST": law_mst,
            "type": "XML",
        }

        response = await self.client.get(
            f"{self.base_url}/lawService.do",
            params=params,
        )
        response.raise_for_status()
        root = ET.fromstring(response.text)

        basic = root.find("./기본정보")
        law_id = self._xml_text(basic, "법령ID")
        law_name = self._xml_text(basic, "법령명_한글")
        law_type = self._xml_text(basic, "법종구분")
        proclaimed_date = self._xml_text(basic, "공포일자")
        enforced_date = self._xml_text(basic, "시행일자")
        revision_type = self._xml_text(basic, "제개정구분")
        revision_reason = self._xml_text(root.find("./제개정이유"), "제개정이유내용")
        amendment_content = self._xml_text(root.find("./개정문"), "개정문내용")

        article_nodes = root.findall("./조문/조문단위")
        articles_data = []
        for node in article_nodes:
            articles_data.append({
                "조문번호": self._xml_text(node, "조문번호"),
                "조문제목": self._xml_text(node, "조문제목"),
                "조문내용": self._xml_text(node, "조문내용"),
                "조문제개정유형": self._xml_text(node, "조문제개정유형"),
                "조문변경여부": self._xml_text(node, "조문변경여부"),
            })

        return LawDetail(
            law_id=law_id,
            law_mst=law_mst,
            law_name=law_name,
            law_type=law_type,
            proclaimed_date=proclaimed_date or None,
            enforced_date=enforced_date or None,
            revision_type=revision_type or None,
            revision_reason=revision_reason or None,
            amendment_content=amendment_content or None,
            articles=self._parse_articles(articles_data),
        )

    async def get_law_history(self, law_id: str) -> List[Dict[str, Any]]:
        """Get law revision history"""
        params = {
            "OC": self.api_key,
            "target": "lawHist",
            "ID": law_id,
            "type": "JSON",
        }

        response = await self._request_with_retry(
            "GET",
            f"{self.base_url}/lawHistService.do",
            params=params,
        )

        data = response.json()
        return data.get("법령연혁", {}).get("연혁정보", [])

    def _parse_nested_text(self, data: Any) -> Optional[str]:
        """
        법제처 API의 list[list[str]] 구조를 텍스트로 변환.
        예: [["문장1", "문장2"]] → "문장1\n문장2"
        """
        if data is None:
            return None
        if isinstance(data, str):
            return data.strip() or None
        if isinstance(data, list):
            if len(data) > 0 and isinstance(data[0], list):
                return "\n".join(str(s) for s in data[0]).strip() or None
            elif len(data) > 0 and isinstance(data[0], str):
                return "\n".join(str(s) for s in data).strip() or None
        return self._normalize_text(data) or None

    def _parse_articles(self, articles_data: List[Dict]) -> List[LawArticle]:
        """Parse articles from API response"""
        if isinstance(articles_data, dict):
            articles_data = [articles_data]

        articles = []
        for art in articles_data:
            if not isinstance(art, dict):
                continue

            articles.append(LawArticle(
                article_no=self._normalize_text(art.get("조문번호", "")),
                article_title=self._normalize_text(art.get("조문제목")) or None,
                article_content=self._normalize_text(art.get("조문내용", "")),
                paragraphs=self._parse_paragraphs(art),
                revision_type_detail=self._normalize_text(art.get("조문제개정유형")) or None,
                change_flag=self._normalize_text(art.get("조문변경여부")) or None,
            ))
        return articles

    def _extract_nested_text(self, value: Any) -> Optional[str]:
        """
        법제처 JSON list[list[str]](또는 유사 구조)에서 본문 문자열 복원.
        파싱 실패 시 None 반환 및 로깅.
        """
        try:
            if value is None:
                return None
            if isinstance(value, list):
                if value and isinstance(value[0], list):
                    joined = "\n".join(
                        [self._normalize_text(line) for line in value[0] if self._normalize_text(line)]
                    ).strip()
                    return joined or None
                joined = "\n".join(
                    [self._normalize_text(item) for item in value if self._normalize_text(item)]
                ).strip()
                return joined or None

            normalized = self._normalize_text(value)
            return normalized or None
        except Exception as exc:
            logger.warning("Failed to parse nested law text: %s", exc)
            return None

    def _xml_text(self, node: Optional[ET.Element], tag: str) -> str:
        if node is None:
            return ""
        found = node.find(tag)
        if found is None or found.text is None:
            return ""
        return found.text.strip()

    def _normalize_text(self, value: Any) -> str:
        """
        법제처 API의 비정형 텍스트(list/dict/None)를 문자열로 정규화.
        """
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, (int, float, bool)):
            return str(value)
        if isinstance(value, list):
            parts = [self._normalize_text(item) for item in value]
            return "\n".join([p for p in parts if p]).strip()
        if isinstance(value, dict):
            # content/content태그 우선, 없으면 값들을 순서대로 병합
            if "content" in value:
                return self._normalize_text(value.get("content"))
            parts = [self._normalize_text(v) for v in value.values()]
            return "\n".join([p for p in parts if p]).strip()
        return str(value).strip()

    def _parse_paragraphs(self, article_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        법제처 API 응답의 항/호/목 구조 파싱

        Args:
            article_data: 조문 데이터 (법제처 API 응답)

        Returns:
            파싱된 paragraphs 리스트 (JSONB 저장용)
        """
        paragraphs = []

        # 항 파싱 (법제처 API 응답 구조: article_data.get('항', []))
        para_list = article_data.get('항', [])
        if not isinstance(para_list, list):
            # 단일 항인 경우 리스트로 변환
            para_list = [para_list] if para_list else []

        for para in para_list:
            if not para or not isinstance(para, dict):
                continue

            para_obj = {
                'type': 'paragraph',
                'no': str(para.get('항번호', '')),
                'content': self._normalize_text(para.get('항내용', '')),
                'items': []
            }

            # 호 파싱
            item_list = para.get('호', [])
            if not isinstance(item_list, list):
                item_list = [item_list] if item_list else []

            for item in item_list:
                if not item or not isinstance(item, dict):
                    continue

                item_obj = {
                    'type': 'item',
                    'no': str(item.get('호번호', '')),
                    'content': self._normalize_text(item.get('호내용', '')),
                    'subitems': []
                }

                # 목 파싱
                subitem_list = item.get('목', [])
                if not isinstance(subitem_list, list):
                    subitem_list = [subitem_list] if subitem_list else []

                for subitem in subitem_list:
                    if not subitem or not isinstance(subitem, dict):
                        continue

                    subitem_obj = {
                        'type': 'subitem',
                        'no': str(subitem.get('목번호', '')),
                        'content': self._normalize_text(subitem.get('목내용', ''))
                    }
                    item_obj['subitems'].append(subitem_obj)

                para_obj['items'].append(item_obj)

            paragraphs.append(para_obj)

        return paragraphs

    async def get_linked_ordinances(
        self,
        org: str = "6110000",
        sborg: str = "3220000",
    ) -> List[LinkedOrdinance]:
        """
        연계 조례 목록 조회 (lnkOrg API)
        자치법규와 상위법령의 연계 정보를 가져옴

        Args:
            org: 도/특별시/광역시 코드 (기본: 서울특별시)
            sborg: 시/군/구 코드 (기본: 강남구)

        Returns:
            연계 조례 목록
        """
        all_items: List[LinkedOrdinance] = []
        page = 1
        max_display = 100

        while True:
            params = {
                "OC": self.api_key,
                "target": "lnkOrg",
                "org": sborg,  # lnkOrg는 sborg 코드 사용
                "type": "JSON",
                "display": max_display,
                "page": page,
            }

            try:
                response = await self._request_with_retry(
                    "GET",
                    f"{self.base_url}/lawSearch.do",
                    params=params,
                )
            except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError):
                logger.warning("연계 조례 조회 실패 (page=%d), 중단합니다", page)
                break

            # HTML 응답 체크 (에러 페이지)
            if response.text.strip().startswith('<!DOCTYPE'):
                break
            data = response.json()

            lnk_org_search = data.get("lnkOrgSearch", {})
            if not lnk_org_search:
                break

            items = lnk_org_search.get("law", [])
            if isinstance(items, dict):
                items = [items]

            if not items:
                break

            for item in items:
                all_items.append(LinkedOrdinance(
                    ordinance_id=item.get("자치법규ID", ""),
                    ordinance_serial_no=item.get("자치법규일련번호", ""),
                    ordinance_name=item.get("자치법규명", ""),
                    ordinance_type=item.get("자치법규종류", ""),
                    law_id=item.get("법령ID", ""),
                    law_name=item.get("법령명한글", ""),
                    enacted_date=item.get("공포일자"),
                    enforced_date=item.get("시행일자"),
                    revision_type=item.get("제개정구분명"),
                ))

            total_cnt = int(lnk_org_search.get("totalCnt", 0))
            if len(all_items) >= total_cnt:
                break

            page += 1
            await asyncio.sleep(0.3)  # Rate limiting

        return all_items

    async def get_ordinance_detail(self, serial_no: str) -> OrdinanceDetail:
        """자치법규 본문 상세 조회 (JSON first, XML fallback)."""
        try:
            return await self._get_ordinance_detail_json(serial_no)
        except Exception as json_error:
            logger.warning(
                "JSON ordinance detail parsing failed for MST=%s, trying XML fallback: %s",
                serial_no,
                json_error,
            )
            try:
                return await self._get_ordinance_detail_xml(serial_no)
            except Exception as xml_error:
                logger.error(
                    "XML fallback failed for ordinance MST=%s: %s",
                    serial_no,
                    xml_error,
                )
                raise

    async def _get_ordinance_detail_json(self, serial_no: str) -> OrdinanceDetail:
        params = {
            "OC": self.api_key,
            "target": "ordin",
            "MST": serial_no,
            "type": "JSON",
        }

        response = await self._request_with_retry(
            "GET",
            f"{self.base_url}/lawService.do",
            params=params,
        )

        data = response.json()

        # 법제처 API 응답 구조 호환: "자치법규" 또는 "LawService" 루트 키
        ordin_data = data.get("자치법규", {})
        if not ordin_data:
            ordin_data = data.get("LawService", {})

        # 기본정보 키 호환: "기본정보" 또는 "자치법규기본정보"
        basic_info = ordin_data.get("기본정보", {})
        if not basic_info:
            basic_info = ordin_data.get("자치법규기본정보", {})

        # 제개정이유/개정문 파싱
        revision_reason = self._parse_nested_text(
            ordin_data.get("제개정이유", {}).get("제개정이유내용")
        )
        amendment_content = self._parse_nested_text(
            ordin_data.get("개정문", {}).get("개정문내용")
        )

        # 조문 키 호환: "조문단위" 또는 "조"
        articles_section = ordin_data.get("조문", {})
        articles_raw = articles_section.get("조문단위", [])
        if not articles_raw:
            articles_raw = articles_section.get("조", [])

        return OrdinanceDetail(
            ordinance_id=self._normalize_text(basic_info.get("자치법규ID", "")),
            serial_no=serial_no,
            ordinance_name=self._normalize_text(basic_info.get("자치법규명", "")),
            ordinance_type=self._normalize_text(basic_info.get("자치법규종류")) or None,
            proclaimed_date=self._normalize_text(basic_info.get("공포일자")) or None,
            enforced_date=self._normalize_text(basic_info.get("시행일자")) or None,
            revision_reason=revision_reason,
            amendment_content=amendment_content,
            articles=self._parse_ordinance_articles(articles_raw),
        )

    async def _get_ordinance_detail_xml(self, serial_no: str) -> OrdinanceDetail:
        params = {
            "OC": self.api_key,
            "target": "ordin",
            "MST": serial_no,
            "type": "XML",
        }

        response = await self.client.get(
            f"{self.base_url}/lawService.do",
            params=params,
        )
        response.raise_for_status()
        root = ET.fromstring(response.text)

        basic = root.find("./기본정보")
        revision_reason = self._xml_text(root.find("./제개정이유"), "제개정이유내용")
        amendment_content = self._xml_text(root.find("./개정문"), "개정문내용")

        article_nodes = root.findall("./조문/조문단위")
        articles_data = []
        for node in article_nodes:
            articles_data.append({
                "조문번호": self._xml_text(node, "조문번호"),
                "조문여부": self._xml_text(node, "조문여부"),
                "조제목": self._xml_text(node, "조제목"),
                "조내용": self._xml_text(node, "조내용"),
            })

        return OrdinanceDetail(
            ordinance_id=self._xml_text(basic, "자치법규ID"),
            serial_no=serial_no,
            ordinance_name=self._xml_text(basic, "자치법규명"),
            ordinance_type=self._xml_text(basic, "자치법규종류") or None,
            proclaimed_date=self._xml_text(basic, "공포일자") or None,
            enforced_date=self._xml_text(basic, "시행일자") or None,
            revision_reason=revision_reason or None,
            amendment_content=amendment_content or None,
            articles=self._parse_ordinance_articles(articles_data),
        )

    def _parse_ordinance_articles(self, articles_data: List[Dict]) -> List[LawArticle]:
        """자치법규 조문 파싱 (조내용/조제목 필드명 사용)"""
        if isinstance(articles_data, dict):
            articles_data = [articles_data]

        articles = []
        for art in articles_data:
            if not isinstance(art, dict):
                continue

            # 조문여부가 N이면 편/장/절/관 — 건너뛰기
            if self._normalize_text(art.get("조문여부")) == "N":
                continue

            # 조문번호가 리스트일 수 있음 (예: ["000100", "000100"]) — 첫 번째 값 사용
            article_no_raw = art.get("조문번호", "")
            if isinstance(article_no_raw, list):
                article_no_raw = article_no_raw[0] if article_no_raw else ""

            articles.append(LawArticle(
                article_no=self._normalize_text(article_no_raw),
                article_title=self._normalize_text(art.get("조제목")) or None,
                article_content=self._normalize_text(art.get("조내용", "")),
                paragraphs=self._parse_paragraphs(art),
            ))
        return articles

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
