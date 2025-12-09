"""
MOLEG (법제처) API Client
"""
import asyncio
from typing import Optional, List, Dict, Any
import httpx
from pydantic import BaseModel


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
    paragraphs: List[Dict[str, Any]] = []


class LawDetail(BaseModel):
    """Law detail"""
    law_id: str
    law_mst: str
    law_name: str
    law_type: str
    proclaimed_date: Optional[str] = None
    enforced_date: Optional[str] = None
    revision_type: Optional[str] = None
    articles: List[LawArticle] = []


class MolegClient:
    """MOLEG Open API client"""

    def __init__(self, api_key: str, base_url: str = "https://www.law.go.kr/DRF"):
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)

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

        response = await self.client.get(
            f"{self.base_url}/lawSearch.do",
            params=params,
        )
        response.raise_for_status()

        data = response.json()
        return data.get("LawSearch", {}).get("law", [])

    async def get_law_detail(self, law_mst: str) -> LawDetail:
        """Get law detail by MST"""
        params = {
            "OC": self.api_key,
            "target": "law",
            "MST": law_mst,
            "type": "JSON",
        }

        response = await self.client.get(
            f"{self.base_url}/lawService.do",
            params=params,
        )
        response.raise_for_status()

        data = response.json()
        law_data = data.get("법령", {})

        return LawDetail(
            law_id=law_data.get("법령ID", ""),
            law_mst=law_mst,
            law_name=law_data.get("법령명_한글", ""),
            law_type=law_data.get("법령종류", ""),
            proclaimed_date=law_data.get("공포일자"),
            enforced_date=law_data.get("시행일자"),
            revision_type=law_data.get("제개정구분"),
            articles=self._parse_articles(law_data.get("조문", [])),
        )

    async def get_law_history(self, law_id: str) -> List[Dict[str, Any]]:
        """Get law revision history"""
        params = {
            "OC": self.api_key,
            "target": "lawHist",
            "ID": law_id,
            "type": "JSON",
        }

        response = await self.client.get(
            f"{self.base_url}/lawHistService.do",
            params=params,
        )
        response.raise_for_status()

        data = response.json()
        return data.get("법령연혁", {}).get("연혁정보", [])

    def _parse_articles(self, articles_data: List[Dict]) -> List[LawArticle]:
        """Parse articles from API response"""
        articles = []
        for art in articles_data:
            articles.append(LawArticle(
                article_no=art.get("조문번호", ""),
                article_title=art.get("조문제목"),
                article_content=art.get("조문내용", ""),
                paragraphs=art.get("항", []),
            ))
        return articles

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

            response = await self.client.get(
                f"{self.base_url}/lawSearch.do",
                params=params,
            )

            # HTML 응답 체크 (에러 페이지)
            if response.text.strip().startswith('<!DOCTYPE'):
                break

            response.raise_for_status()
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

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
