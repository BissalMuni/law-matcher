"""
Law Sync Service - 상위법령 동기화 및 개정 감지 서비스

법제처 현행법령 API (target=law)를 통해 상위법령을 조회하고,
공포일자 변경을 감지하여 조례 개정 대상을 식별합니다.
"""
import asyncio
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
import httpx
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.law import Law
from backend.models.ordinance import Ordinance
from backend.models.ordinance_law_mapping import OrdinanceLawMapping
from backend.models.amendment import LawAmendment
from backend.core.config import settings


class LawSearchResult:
    """법령 검색 API 응답 파싱 결과"""

    def __init__(self, data: Dict[str, Any]):
        self.law_serial_no = int(data.get("법령일련번호", 0))
        self.law_id = int(data.get("법령ID", 0))
        self.law_name = data.get("법령명한글", "")
        self.law_abbr = data.get("법령약칭명")
        self.law_type = data.get("법령구분명", "")
        self.history_code = data.get("현행연혁코드")
        self.revision_type = data.get("제개정구분명")
        self.dept_name = data.get("소관부처명")
        self.dept_code = int(data.get("소관부처코드", 0)) if data.get("소관부처코드") else None
        self.joint_dept_info = data.get("공동부령구분")
        self.joint_proclaimed_no = data.get("공포번호")  # 공동부령용
        self.self_other_law = data.get("자법타법여부")
        self.detail_link = data.get("법령상세링크")

        # 날짜 파싱
        self.proclaimed_date = self._parse_date(data.get("공포일자"))
        self.proclaimed_no = int(data.get("공포번호", 0)) if data.get("공포번호") else None
        self.enforced_date = self._parse_date(data.get("시행일자"))

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """YYYYMMDD 형식 날짜 파싱"""
        if not date_str:
            return None
        try:
            return datetime.strptime(str(date_str), "%Y%m%d").date()
        except (ValueError, TypeError):
            return None


class LawSyncService:
    """상위법령 동기화 서비스"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.api_key = settings.MOLEG_API_KEY or "test"
        self.base_url = "http://www.law.go.kr/DRF/lawSearch.do"
        self.timeout = 60.0

    async def search_laws(
        self,
        query: Optional[str] = None,
        anc_yd: Optional[str] = None,  # 공포일자 범위 (20090101~20090130)
        revision_type: Optional[str] = None,  # 제개정구분 코드
        page: int = 1,
        display: int = 100,
        sort: str = "ddes",  # 공포일자 내림차순
    ) -> Tuple[List[LawSearchResult], int]:
        """
        현행법령 검색 API 호출

        Args:
            query: 법령명 검색어
            anc_yd: 공포일자 범위 (YYYYMMDD~YYYYMMDD)
            revision_type: 제개정 구분 코드 (300201=제정, 300202=일부개정 등)
            page: 페이지 번호
            display: 결과 개수 (max 100)
            sort: 정렬 옵션

        Returns:
            (검색결과 리스트, 전체 개수)
        """
        params = {
            "OC": self.api_key,
            "target": "law",
            "type": "JSON",
            "page": page,
            "display": display,
            "sort": sort,
        }

        if query:
            params["query"] = query
        if anc_yd:
            params["ancYd"] = anc_yd
        if revision_type:
            params["rrClsCd"] = revision_type

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(self.base_url, params=params)

            # HTML 에러 페이지 체크
            if response.text.strip().startswith("<!DOCTYPE"):
                return [], 0

            response.raise_for_status()
            data = response.json()

        law_search = data.get("LawSearch") or data.get("lawSearch", {})
        if not law_search:
            return [], 0

        total_cnt = int(law_search.get("totalCnt", 0))
        items = law_search.get("law", [])

        if isinstance(items, dict):
            items = [items]

        results = [LawSearchResult(item) for item in items]
        return results, total_cnt

    async def search_all_laws(
        self,
        query: Optional[str] = None,
        anc_yd: Optional[str] = None,
        revision_type: Optional[str] = None,
    ) -> List[LawSearchResult]:
        """모든 페이지 조회하여 전체 결과 반환"""
        all_results: List[LawSearchResult] = []
        page = 1

        while True:
            results, total_cnt = await self.search_laws(
                query=query,
                anc_yd=anc_yd,
                revision_type=revision_type,
                page=page,
            )

            if not results:
                break

            all_results.extend(results)

            if len(all_results) >= total_cnt:
                break

            page += 1
            await asyncio.sleep(0.3)  # Rate limiting

        return all_results

    async def sync_law(self, search_result: LawSearchResult) -> Law:
        """
        단일 법령 동기화 (upsert)

        Returns:
            저장/업데이트된 Law 객체
        """
        # 기존 레코드 조회
        stmt = select(Law).where(Law.law_serial_no == search_result.law_serial_no)
        result = await self.db.execute(stmt)
        existing_law = result.scalar_one_or_none()

        if existing_law:
            # 업데이트
            existing_law.law_id = search_result.law_id
            existing_law.law_name = search_result.law_name
            existing_law.law_abbr = search_result.law_abbr
            existing_law.law_type = search_result.law_type
            existing_law.proclaimed_date = search_result.proclaimed_date
            existing_law.proclaimed_no = search_result.proclaimed_no
            existing_law.enforced_date = search_result.enforced_date
            existing_law.revision_type = search_result.revision_type
            existing_law.history_code = search_result.history_code
            existing_law.dept_name = search_result.dept_name
            existing_law.dept_code = search_result.dept_code
            existing_law.joint_dept_info = search_result.joint_dept_info
            existing_law.joint_proclaimed_no = search_result.joint_proclaimed_no
            existing_law.self_other_law = search_result.self_other_law
            existing_law.detail_link = search_result.detail_link
            existing_law.last_synced_at = datetime.utcnow()
            return existing_law
        else:
            # 신규 생성
            new_law = Law(
                law_serial_no=search_result.law_serial_no,
                law_id=search_result.law_id,
                law_name=search_result.law_name,
                law_abbr=search_result.law_abbr,
                law_type=search_result.law_type,
                proclaimed_date=search_result.proclaimed_date,
                proclaimed_no=search_result.proclaimed_no,
                enforced_date=search_result.enforced_date,
                revision_type=search_result.revision_type,
                history_code=search_result.history_code,
                dept_name=search_result.dept_name,
                dept_code=search_result.dept_code,
                joint_dept_info=search_result.joint_dept_info,
                joint_proclaimed_no=search_result.joint_proclaimed_no,
                self_other_law=search_result.self_other_law,
                detail_link=search_result.detail_link,
                last_synced_at=datetime.utcnow(),
            )
            self.db.add(new_law)
            return new_law

    async def sync_laws_by_names(self, law_names: List[str]) -> Dict[str, Any]:
        """
        법령명 목록으로 법령 동기화

        Returns:
            {"synced": 동기화 수, "failed": 실패 수, "laws": Law 객체 리스트}
        """
        synced = 0
        failed = 0
        laws: List[Law] = []

        for law_name in law_names:
            try:
                results, _ = await self.search_laws(query=law_name, display=1)
                if results:
                    law = await self.sync_law(results[0])
                    laws.append(law)
                    synced += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"Failed to sync law '{law_name}': {e}")
                failed += 1
            await asyncio.sleep(0.3)

        await self.db.commit()

        return {
            "synced": synced,
            "failed": failed,
            "laws": laws,
        }

    async def check_amendments(
        self,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        최근 N일간 공포된 법령 중 개정된 법령을 확인하고,
        해당 법령과 연계된 조례를 개정 대상으로 식별

        Args:
            days: 검색할 일수 (기본 30일)

        Returns:
            개정 감지 결과 리스트
        """
        # 공포일자 범위 설정
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        anc_yd = f"{start_date.strftime('%Y%m%d')}~{end_date.strftime('%Y%m%d')}"

        # 일부개정(300202) + 전부개정(300203) 법령 조회
        amendment_results: List[Dict[str, Any]] = []

        for revision_code in ["300202", "300203"]:
            api_results = await self.search_all_laws(
                anc_yd=anc_yd,
                revision_type=revision_code,
            )

            for api_law in api_results:
                # DB에서 해당 법령 조회
                stmt = select(Law).where(Law.law_serial_no == api_law.law_serial_no)
                result = await self.db.execute(stmt)
                db_law = result.scalar_one_or_none()

                if not db_law:
                    continue

                # 공포일자 비교 - 개정 감지
                if db_law.proclaimed_date and api_law.proclaimed_date:
                    if api_law.proclaimed_date > db_law.proclaimed_date:
                        # 개정된 법령 발견!
                        affected_ordinances = await self._get_affected_ordinances(db_law.id)

                        amendment_results.append({
                            "law": db_law,
                            "old_proclaimed_date": db_law.proclaimed_date,
                            "new_proclaimed_date": api_law.proclaimed_date,
                            "revision_type": api_law.revision_type,
                            "affected_ordinances": affected_ordinances,
                        })

                        # 법령 정보 업데이트
                        await self.sync_law(api_law)

        await self.db.commit()
        return amendment_results

    async def _get_affected_ordinances(self, law_id: int) -> List[Ordinance]:
        """법령과 연계된 조례 목록 조회"""
        stmt = (
            select(Ordinance)
            .join(OrdinanceLawMapping)
            .where(OrdinanceLawMapping.law_id == law_id)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_amendment_targets(
        self,
        amendment_results: List[Dict[str, Any]],
    ) -> List[LawAmendment]:
        """
        개정 감지 결과를 바탕으로 개정 대상 레코드 생성

        Args:
            amendment_results: check_amendments 결과

        Returns:
            생성된 LawAmendment 리스트
        """
        amendments: List[LawAmendment] = []

        for result in amendment_results:
            law: Law = result["law"]
            ordinances: List[Ordinance] = result["affected_ordinances"]

            for ordinance in ordinances:
                # 중복 체크
                stmt = select(LawAmendment).where(
                    and_(
                        LawAmendment.ordinance_id == ordinance.id,
                        LawAmendment.status == "PENDING",
                    )
                )
                existing = await self.db.execute(stmt)
                if existing.scalar_one_or_none():
                    continue

                amendment = LawAmendment(
                    ordinance_id=ordinance.id,
                    change_type="REVISION",
                    description=f"상위법령 '{law.law_name}' 개정 ({result['revision_type']})",
                    source_law_name=law.law_name,
                    source_proclaimed_date=result["new_proclaimed_date"],
                    status="PENDING",
                )
                self.db.add(amendment)
                amendments.append(amendment)

        await self.db.commit()
        return amendments

    async def sync_from_lnk_org(
        self,
        sborg: str = "3220000",
    ) -> Dict[str, Any]:
        """
        lnkOrg API에서 조례-법령 연계 정보를 가져와서
        laws 테이블과 ordinance_law_mappings 테이블을 동기화

        Args:
            sborg: 지자체 코드

        Returns:
            동기화 결과
        """
        all_items = await self._fetch_lnk_org_data(sborg)

        synced_laws = 0
        synced_mappings = 0
        errors = []

        # 법령 ID -> 법령 정보 매핑
        law_id_to_info: Dict[str, Dict] = {}
        for item in all_items:
            law_id = item.get("법령ID", "")
            if law_id and law_id not in law_id_to_info:
                law_id_to_info[law_id] = {
                    "law_name": item.get("법령명한글", ""),
                    "proclaimed_date": item.get("공포일자"),
                    "enforced_date": item.get("시행일자"),
                }

        # 법령 정보로 laws 테이블 동기화
        for law_id_str, info in law_id_to_info.items():
            try:
                # 법령명으로 검색하여 상세 정보 가져오기
                results, _ = await self.search_laws(query=info["law_name"], display=1)
                if results:
                    await self.sync_law(results[0])
                    synced_laws += 1
                await asyncio.sleep(0.2)
            except Exception as e:
                errors.append(f"Failed to sync law {info['law_name']}: {e}")

        await self.db.commit()

        # ordinance_law_mappings 동기화
        for item in all_items:
            try:
                ordinance_serial_no = item.get("자치법규일련번호", "")
                law_name = item.get("법령명한글", "")

                if not ordinance_serial_no or not law_name:
                    continue

                # Ordinance 조회
                stmt = select(Ordinance).where(Ordinance.serial_no == ordinance_serial_no)
                result = await self.db.execute(stmt)
                ordinance = result.scalar_one_or_none()

                if not ordinance:
                    continue

                # Law 조회
                stmt = select(Law).where(Law.law_name == law_name)
                result = await self.db.execute(stmt)
                law = result.scalar_one_or_none()

                if not law:
                    continue

                # 매핑 생성 (중복 체크)
                stmt = select(OrdinanceLawMapping).where(
                    and_(
                        OrdinanceLawMapping.ordinance_id == ordinance.id,
                        OrdinanceLawMapping.law_id == law.id,
                    )
                )
                result = await self.db.execute(stmt)
                existing = result.scalar_one_or_none()

                if not existing:
                    mapping = OrdinanceLawMapping(
                        ordinance_id=ordinance.id,
                        law_id=law.id,
                    )
                    self.db.add(mapping)
                    synced_mappings += 1

            except Exception as e:
                errors.append(f"Failed to create mapping: {e}")

        await self.db.commit()

        return {
            "synced_laws": synced_laws,
            "synced_mappings": synced_mappings,
            "total_items": len(all_items),
            "errors": errors,
        }

    async def _fetch_lnk_org_data(self, sborg: str) -> List[Dict[str, Any]]:
        """lnkOrg API에서 연계 데이터 조회"""
        all_items: List[Dict] = []
        page = 1

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            while True:
                params = {
                    "OC": self.api_key,
                    "target": "lnkOrg",
                    "org": sborg,
                    "type": "JSON",
                    "display": 100,
                    "page": page,
                }

                response = await client.get(self.base_url, params=params)

                if response.text.strip().startswith("<!DOCTYPE"):
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

                all_items.extend(items)

                total_cnt = int(lnk_org_search.get("totalCnt", 0))
                if len(all_items) >= total_cnt:
                    break

                page += 1
                await asyncio.sleep(0.3)

        return all_items

    async def get_law_by_name(self, law_name: str) -> Optional[Law]:
        """법령명으로 Law 조회"""
        stmt = select(Law).where(Law.law_name == law_name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_law_by_serial_no(self, serial_no: int) -> Optional[Law]:
        """법령일련번호로 Law 조회"""
        stmt = select(Law).where(Law.law_serial_no == serial_no)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_laws_needing_sync(self, days_threshold: int = 7) -> List[Law]:
        """마지막 동기화 이후 N일이 지난 법령 목록"""
        threshold = datetime.utcnow() - timedelta(days=days_threshold)
        stmt = select(Law).where(
            (Law.last_synced_at == None) | (Law.last_synced_at < threshold)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
