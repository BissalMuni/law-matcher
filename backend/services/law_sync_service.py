"""
Law Sync Service - 상위법령 동기화 및 개정 감지 서비스

법제처 현행법령 API (target=law)를 통해 상위법령을 조회하고,
공포일자 변경을 감지하여 조례 개정 대상을 식별합니다.
"""
import asyncio
import logging
import uuid
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
import httpx
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)

from backend.models.law import Law
from backend.models.ordinance import Ordinance
from backend.models.ordinance_law_mapping import OrdinanceLawMapping
from backend.models.amendment import LawAmendment
from backend.models.law_change import LawChange, ApiStatus
from backend.core.config import settings
from backend.external.moleg_client import MolegClient


class LawSearchResult:
    """법령 검색 API 응답 파싱 결과"""

    def __init__(self, data: Dict[str, Any]):
        import re
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

        # detail_link의 MST가 실제 상세조회용 키 (법령일련번호와 다를 수 있음)
        if self.detail_link:
            match = re.search(r"MST=(\d+)", self.detail_link)
            if match:
                self.law_serial_no = int(match.group(1))

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

        max_retries = 2
        last_exc = None

        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(self.base_url, params=params)

                    # HTML 에러 페이지 체크
                    if response.text.strip().startswith("<!DOCTYPE"):
                        return [], 0

                    response.raise_for_status()

                    try:
                        data = response.json()
                    except Exception as json_err:
                        logger.warning(
                            "법령 검색 API JSON 파싱 실패 (시도 %d/%d): %s",
                            attempt + 1, max_retries + 1, json_err,
                        )
                        if attempt < max_retries:
                            await asyncio.sleep(1.0 * (2 ** attempt))
                            continue
                        return [], 0

                law_search = data.get("LawSearch") or data.get("lawSearch", {})
                if not law_search:
                    return [], 0

                total_cnt = int(law_search.get("totalCnt", 0))
                items = law_search.get("law", [])

                if isinstance(items, dict):
                    items = [items]

                results = [LawSearchResult(item) for item in items]
                return results, total_cnt

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_exc = e
                if attempt < max_retries:
                    delay = 1.0 * (2 ** attempt)
                    logger.warning(
                        "법령 검색 API 요청 실패 (시도 %d/%d), %s초 후 재시도: %s",
                        attempt + 1, max_retries + 1, delay, str(e),
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error("법령 검색 API 요청 최종 실패: %s", str(e))
                    raise
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500 and attempt < max_retries:
                    delay = 1.0 * (2 ** attempt)
                    logger.warning(
                        "법령 검색 API 서버 오류 %d (시도 %d/%d), %s초 후 재시도",
                        e.response.status_code, attempt + 1, max_retries + 1, delay,
                    )
                    await asyncio.sleep(delay)
                    last_exc = e
                else:
                    raise

        raise last_exc  # type: ignore

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
        # law_id 기준으로 조회 (법령당 최신 개정본 1건 유지)
        stmt = select(Law).where(Law.law_id == search_result.law_id)
        result = await self.db.execute(stmt)
        existing_law = result.scalar_one_or_none()

        if existing_law:
            # 업데이트 (개정 시 law_serial_no도 갱신)
            existing_law.law_serial_no = search_result.law_serial_no
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
                logger.error("법령 '%s' 동기화 실패: %s", law_name, e)
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
                errors.append(f"법령 '{info['law_name']}' 동기화 실패: {e}")

        await self.db.commit()

        # ordinance_law_mappings 동기화
        for item in all_items:
            try:
                ordinance_serial_no = item.get("자치법규일련번호", "")
                law_name = item.get("법령명한글", "")
                law_id_str = item.get("법령ID", "")

                if not ordinance_serial_no or (not law_id_str and not law_name):
                    continue

                # Ordinance 조회
                stmt = select(Ordinance).where(Ordinance.serial_no == ordinance_serial_no)
                result = await self.db.execute(stmt)
                ordinance = result.scalar_one_or_none()

                if not ordinance:
                    continue

                # Law 조회: 법령ID 우선, 없으면 법령명으로 fallback
                law = None
                if law_id_str:
                    try:
                        stmt = select(Law).where(Law.law_id == int(law_id_str))
                        result = await self.db.execute(stmt)
                        law = result.scalar_one_or_none()
                    except (ValueError, TypeError):
                        pass
                if not law and law_name:
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
                errors.append(f"매핑 생성 실패: {e}")

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

                try:
                    response = await client.get(self.base_url, params=params)
                except (httpx.TimeoutException, httpx.ConnectError) as e:
                    logger.warning("lnkOrg API 요청 실패 (page=%d): %s", page, e)
                    break

                if response.text.strip().startswith("<!DOCTYPE"):
                    break

                try:
                    data = response.json()
                except Exception:
                    logger.warning("lnkOrg API JSON 파싱 실패 (page=%d)", page)
                    break
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

    @staticmethod
    def _normalize_law_name(name: Optional[str]) -> str:
        if not name:
            return ""
        return "".join(str(name).split())

    @staticmethod
    def _parse_api_date(date_value: Optional[str]) -> Optional[date]:
        if not date_value:
            return None
        value = str(date_value).strip()
        for fmt in ("%Y%m%d", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        return None

    def _find_exact_match(
        self,
        results: List[LawSearchResult],
        target_name: str,
    ) -> Optional[LawSearchResult]:
        # 1) 완전 일치 우선
        for item in results:
            if item.law_name == target_name:
                return item

        # 2) 공백 제거 정규화 일치 허용
        target_normalized = self._normalize_law_name(target_name)
        for item in results:
            if self._normalize_law_name(item.law_name) == target_normalized:
                return item

        return None

    def _to_search_result_from_detail(self, law_detail: Any) -> LawSearchResult:
        raw = {
            "법령일련번호": law_detail.law_mst,
            "법령ID": law_detail.law_id,
            "법령명한글": law_detail.law_name,
            "법령구분명": law_detail.law_type,
            "공포일자": law_detail.proclaimed_date,
            "시행일자": law_detail.enforced_date,
            "제개정구분명": law_detail.revision_type,
        }
        result = LawSearchResult(raw)
        # lawService의 날짜가 YYYY-MM-DD로 내려오는 경우를 보정
        if result.proclaimed_date is None:
            result.proclaimed_date = self._parse_api_date(law_detail.proclaimed_date)
        if result.enforced_date is None:
            result.enforced_date = self._parse_api_date(law_detail.enforced_date)
        return result

    async def _resolve_exact_match(
        self,
        law: Law,
        moleg_client: MolegClient,
    ) -> Tuple[Optional[LawSearchResult], List[LawSearchResult], bool]:
        """
        법령 매칭 우선순위:
        1) MST(법령일련번호)로 직접 조회
        2) 법령명 검색(검색폭 확대 + 재시도)
        """
        # 1) MST 직접 조회 (가장 안정적) — detail_link의 MST 우선 사용
        mst = law.effective_mst
        if mst:
            try:
                law_detail = await moleg_client.get_law_detail(mst)
                if law_detail and law_detail.law_name:
                    by_mst = self._to_search_result_from_detail(law_detail)
                    if self._normalize_law_name(by_mst.law_name) == self._normalize_law_name(law.law_name):
                        return by_mst, [by_mst], True
            except Exception:
                # MST 직접 조회 실패 시 검색으로 폴백
                pass

        # 2) 법령명 검색 (재시도 + display 확장)
        queries = [law.law_name]
        compact_name = self._normalize_law_name(law.law_name)
        if compact_name and compact_name != law.law_name:
            queries.append(compact_name)

        last_results: List[LawSearchResult] = []
        had_response = False
        for query in queries:
            results, _ = await self.search_laws(query=query, display=30)
            if results:
                had_response = True
                last_results = results
                exact_match = self._find_exact_match(results, law.law_name)
                if exact_match:
                    return exact_match, results, True
            await asyncio.sleep(0.2)

        return None, last_results, had_response

    async def update_all_law_info(self) -> Dict[str, Any]:
        """
        모든 상위법령의 정보를 법제처 API로 업데이트

        laws 테이블의 모든 법령명에 대해 법제처 API를 호출하여
        공포일, 시행일, 법령ID 등 정보를 업데이트합니다.

        Returns:
            {"total_laws": 전체 법령 수, "updated": 업데이트 수, "failed": 실패 수}
        """
        # 모든 법령 조회
        stmt = select(Law)
        result = await self.db.execute(stmt)
        all_laws = list(result.scalars().all())

        total_laws = len(all_laws)
        updated = 0
        failed = 0

        moleg_client = MolegClient(api_key=self.api_key, base_url=settings.MOLEG_API_BASE_URL)
        try:
            for law in all_laws:
                try:
                    exact_match, _, _ = await self._resolve_exact_match(law, moleg_client)

                    if exact_match:
                        # 법령 정보 업데이트
                        law.law_id = exact_match.law_id
                        law.law_serial_no = exact_match.law_serial_no
                        law.law_abbr = exact_match.law_abbr
                        law.proclaimed_date = exact_match.proclaimed_date
                        law.proclaimed_no = exact_match.proclaimed_no
                        law.enforced_date = exact_match.enforced_date
                        law.revision_type = exact_match.revision_type
                        law.history_code = exact_match.history_code
                        law.dept_name = exact_match.dept_name
                        law.dept_code = exact_match.dept_code
                        law.detail_link = exact_match.detail_link
                        law.last_synced_at = datetime.utcnow()
                        updated += 1
                    else:
                        failed += 1

                    # Rate limiting
                    await asyncio.sleep(0.3)

                except Exception as e:
                    logger.error("법령 '%s' 업데이트 실패: %s", law.law_name, e)
                    failed += 1
        finally:
            await moleg_client.close()

        await self.db.commit()

        return {
            "total_laws": total_laws,
            "updated": updated,
            "failed": failed,
        }

    async def update_laws_by_ids(self, law_ids: List[int]) -> Dict[str, Any]:
        """
        특정 법령만 법제처 API로 동기화

        Args:
            law_ids: laws 테이블의 PK(id) 목록

        Returns:
            {"total_laws": 전체 법령 수, "updated": 업데이트 수, "failed": 실패 수}
        """
        stmt = select(Law).where(Law.id.in_(law_ids))
        result = await self.db.execute(stmt)
        laws = list(result.scalars().all())

        total_laws = len(laws)
        updated = 0
        failed = 0

        moleg_client = MolegClient(api_key=self.api_key, base_url=settings.MOLEG_API_BASE_URL)
        try:
            for law in laws:
                try:
                    exact_match, _, _ = await self._resolve_exact_match(law, moleg_client)

                    if exact_match:
                        law.law_id = exact_match.law_id
                        law.law_serial_no = exact_match.law_serial_no
                        law.law_abbr = exact_match.law_abbr
                        law.proclaimed_date = exact_match.proclaimed_date
                        law.proclaimed_no = exact_match.proclaimed_no
                        law.enforced_date = exact_match.enforced_date
                        law.revision_type = exact_match.revision_type
                        law.history_code = exact_match.history_code
                        law.dept_name = exact_match.dept_name
                        law.dept_code = exact_match.dept_code
                        law.detail_link = exact_match.detail_link
                        law.last_synced_at = datetime.utcnow()
                        updated += 1
                    else:
                        failed += 1

                    await asyncio.sleep(0.3)

                except Exception as e:
                    logger.error("법령 '%s' 업데이트 실패: %s", law.law_name, e)
                    failed += 1
        finally:
            await moleg_client.close()

        await self.db.commit()

        return {
            "total_laws": total_laws,
            "updated": updated,
            "failed": failed,
        }

    async def sync_all_laws_with_progress(self, save_to_db: bool = True):
        """
        모든 상위법령을 법제처 API와 동기화하고 변경사항을 추적 (SSE 스트리밍용 제너레이터)

        Args:
            save_to_db: True이면 변경사항을 law_changes 테이블에 저장 (기본값: True)

        Yields:
            진행 상황 및 변경된 법령 정보
        """
        moleg_client = MolegClient(api_key=self.api_key, base_url=settings.MOLEG_API_BASE_URL)

        # 모든 법령 조회
        stmt = select(Law).order_by(Law.id)
        result = await self.db.execute(stmt)
        all_laws = list(result.scalars().all())
        # rollback 시 expired 객체의 id 접근 불가 방지용 캐시
        all_law_ids = [law.id for law in all_laws]

        total_laws = len(all_laws)
        updated = 0
        failed = 0
        changed_laws = []

        # 동기화 배치 ID 생성 (같은 동기화 작업 묶기용)
        sync_batch_id = str(uuid.uuid4())[:8]
        sync_date = datetime.utcnow()

        yield {
            "type": "start",
            "total": total_laws,
            "sync_batch_id": sync_batch_id,
            "message": f"동기화 시작: 총 {total_laws}건의 법령",
        }

        try:
            for idx, law in enumerate(all_laws):
                current = idx + 1
                law_name = f"law_id={all_law_ids[idx]}"

                try:
                    # rollback 후 expired 객체 접근 시 greenlet 오류 방지
                    law_name = law.law_name

                    # 요청 시작 알림
                    yield {
                        "type": "progress",
                        "current": current,
                        "total": total_laws,
                        "law_name": law_name,
                        "status": "requesting",
                        "message": f"[{current}/{total_laws}] {law_name} - API 요청 중...",
                    }
                    exact_match, results, had_response = await self._resolve_exact_match(law, moleg_client)

                    # 수신 완료 알림
                    yield {
                        "type": "progress",
                        "current": current,
                        "total": total_laws,
                        "law_name": law_name,
                        "status": "received",
                        "message": f"[{current}/{total_laws}] {law_name} - 응답 수신 ({len(results)}건)",
                    }

                    # API 응답이 없는 경우
                    if not had_response:
                        failed += 1
                        compare_result = "api_no_response"

                    # API 실패 정보 기록
                        failed_law_info = {
                            "id": law.id,
                            "law_id": law.law_id,
                            "law_name": law_name,
                            "law_type": law.law_type,
                            "proclaimed_date": str(law.proclaimed_date) if law.proclaimed_date else None,
                            "enforced_date": str(law.enforced_date) if law.enforced_date else None,
                            "revision_type": law.revision_type,
                            "dept_name": law.dept_name,
                            "api_status": "no_response",
                            "api_message": "API 응답 없음",
                            "changes": {},
                        }
                        changed_laws.append(failed_law_info)

                    # law_changes 테이블에 저장
                        if save_to_db:
                            law_change = LawChange(
                                law_id=law.id,
                                sync_date=sync_date,
                                sync_batch_id=sync_batch_id,
                                api_status=ApiStatus.NO_RESPONSE,
                                api_message="API 응답 없음",
                                old_values={
                                    "proclaimed_date": str(law.proclaimed_date) if law.proclaimed_date else None,
                                    "enforced_date": str(law.enforced_date) if law.enforced_date else None,
                                    "revision_type": law.revision_type,
                                },
                                new_values=None,
                                dept_name=law.dept_name,
                                dept_code=law.dept_code,
                            )
                            self.db.add(law_change)

                        yield {
                            "type": "changed",
                            "current": current,
                            "total": total_laws,
                            "law": failed_law_info,
                            "message": f"[{current}/{total_laws}] {law_name} - API 응답 없음",
                        }
                    elif exact_match:
                    # 변경사항 비교
                        changes = {}
                        old_values = {
                            "proclaimed_date": str(law.proclaimed_date) if law.proclaimed_date else None,
                            "enforced_date": str(law.enforced_date) if law.enforced_date else None,
                            "revision_type": law.revision_type,
                            "law_id": law.law_id,
                        }
                        if law.proclaimed_date != exact_match.proclaimed_date:
                            changes["proclaimed_date"] = {
                                "old": str(law.proclaimed_date) if law.proclaimed_date else None,
                                "new": str(exact_match.proclaimed_date) if exact_match.proclaimed_date else None,
                            }
                        if law.enforced_date != exact_match.enforced_date:
                            changes["enforced_date"] = {
                                "old": str(law.enforced_date) if law.enforced_date else None,
                                "new": str(exact_match.enforced_date) if exact_match.enforced_date else None,
                            }
                        if law.revision_type != exact_match.revision_type:
                            changes["revision_type"] = {
                                "old": law.revision_type,
                                "new": exact_match.revision_type,
                            }
                        if law.law_id != exact_match.law_id:
                            changes["law_id"] = {
                                "old": law.law_id,
                                "new": exact_match.law_id,
                            }

                        # law_id 충돌 체크: 다른 법령이 이미 해당 law_id를 사용 중인지 확인
                        skip_law_id_update = False
                        if exact_match.law_id != law.law_id:
                            conflict_stmt = select(Law.id).where(
                                and_(
                                    Law.law_id == exact_match.law_id,
                                    Law.id != law.id,
                                )
                            )
                            conflict = (await self.db.execute(conflict_stmt)).scalar_one_or_none()
                            if conflict:
                                logger.warning(
                                    "law_id 충돌: %s(id=%d)의 law_id를 %d로 변경 시 "
                                    "기존 법령(id=%d)과 충돌 — law_id 업데이트 생략",
                                    law_name, law.id, exact_match.law_id, conflict,
                                )
                                skip_law_id_update = True
                                changes["law_id"]["skipped"] = True

                        # 법령 정보 업데이트
                        if not skip_law_id_update:
                            law.law_id = exact_match.law_id

                        # law_serial_no 충돌 방지: 같을 때만 업데이트, 다르면 기록만
                        law.law_abbr = exact_match.law_abbr
                        law.proclaimed_date = exact_match.proclaimed_date
                        law.proclaimed_no = exact_match.proclaimed_no
                        law.enforced_date = exact_match.enforced_date
                        law.revision_type = exact_match.revision_type
                        law.history_code = exact_match.history_code
                        law.dept_name = exact_match.dept_name
                        law.dept_code = exact_match.dept_code
                        law.detail_link = exact_match.detail_link
                        law.last_synced_at = datetime.utcnow()

                        if law.law_serial_no != exact_match.law_serial_no:
                            changes["law_serial_no"] = {
                                "old": law.law_serial_no,
                                "new": exact_match.law_serial_no,
                                "skipped": True,
                            }
                        updated += 1

                        compare_result = "changed" if changes else "unchanged"
                        if changes:
                            changed_law_info = {
                                "id": law.id,
                                "law_id": exact_match.law_id,
                                "law_name": law_name,
                                "law_type": exact_match.law_type,
                                "proclaimed_date": str(exact_match.proclaimed_date) if exact_match.proclaimed_date else None,
                                "enforced_date": str(exact_match.enforced_date) if exact_match.enforced_date else None,
                                "revision_type": exact_match.revision_type,
                                "dept_name": exact_match.dept_name,
                                "api_status": "success",
                                "api_message": "API 성공",
                                "changes": changes,
                            }
                            changed_laws.append(changed_law_info)

                            # law_changes 테이블에 저장 (법령 변경이 있는 경우만)
                            if save_to_db and changes:
                                law_change = LawChange(
                                    law_id=law.id,
                                    sync_date=sync_date,
                                    sync_batch_id=sync_batch_id,
                                    api_status=ApiStatus.SUCCESS,
                                    api_message="API 성공 - 변경 감지",
                                    old_values=old_values,
                                    new_values={
                                        "proclaimed_date": str(exact_match.proclaimed_date) if exact_match.proclaimed_date else None,
                                        "enforced_date": str(exact_match.enforced_date) if exact_match.enforced_date else None,
                                        "revision_type": exact_match.revision_type,
                                        "law_id": exact_match.law_id,
                                        "dept_name": exact_match.dept_name,
                                    },
                                    dept_name=exact_match.dept_name,
                                    dept_code=exact_match.dept_code,
                                    )
                                self.db.add(law_change)

                            yield {
                                "type": "changed",
                                "current": current,
                                "total": total_laws,
                                "law": changed_law_info,
                                "message": f"[{current}/{total_laws}] {law_name} - 변경 감지!",
                            }

                        # 매 건마다 flush하여 에러 발생 시 해당 건만 롤백
                        try:
                            await self.db.flush()
                        except Exception as flush_err:
                            logger.error(
                                "DB flush 실패 (law=%s): %s", law_name, flush_err,
                            )
                            await self.db.rollback()
                            # rollback 후 세션의 만료된 객체 사용 불가 → 캐시된 ID로 새로 조회
                            try:
                                remaining_ids = all_law_ids[idx + 1:]
                                if remaining_ids:
                                    stmt_reload = select(Law).where(Law.id.in_(remaining_ids)).order_by(Law.id)
                                    reload_result = await self.db.execute(stmt_reload)
                                    reloaded_laws = list(reload_result.scalars().all())
                                    reloaded_map = {l.id: l for l in reloaded_laws}
                                    for i, lid in enumerate(remaining_ids):
                                        if lid in reloaded_map:
                                            all_laws[idx + 1 + i] = reloaded_map[lid]
                            except Exception as reload_err:
                                logger.error(
                                    "DB 세션 복구 실패: %s — 동기화를 중단합니다", reload_err,
                                )
                                # 복구 불가 시 지금까지 결과 반환하고 종료
                                yield {
                                    "type": "error",
                                    "current": current,
                                    "total": total_laws,
                                    "law_name": law_name,
                                    "error": f"DB 세션 복구 불가: {reload_err}",
                                    "message": f"[{current}/{total_laws}] DB 세션 복구 불가 - 동기화 중단",
                                }
                                break
                            failed += 1
                            yield {
                                "type": "error",
                                "current": current,
                                "total": total_laws,
                                "law_name": law_name,
                                "error": str(flush_err),
                                "message": f"[{current}/{total_laws}] {law_name} - DB 저장 오류: {str(flush_err)}",
                            }
                            continue
                    else:
                    # API 응답은 있지만 정확히 일치하는 법령명 없음
                        failed += 1
                        compare_result = "not_found"

                        api_message = f"정확히 일치하는 법령명 없음 (검색결과: {len(results)}건)"

                    # 법령명 불일치 정보 기록
                        not_found_law_info = {
                            "id": law.id,
                            "law_id": law.law_id,
                            "law_name": law_name,
                            "law_type": law.law_type,
                            "proclaimed_date": str(law.proclaimed_date) if law.proclaimed_date else None,
                            "enforced_date": str(law.enforced_date) if law.enforced_date else None,
                            "revision_type": law.revision_type,
                            "dept_name": law.dept_name,
                            "api_status": "not_found",
                            "api_message": api_message,
                            "changes": {},
                        }
                        changed_laws.append(not_found_law_info)

                    # law_changes 테이블에 저장
                        if save_to_db:
                            law_change = LawChange(
                                law_id=law.id,
                                sync_date=sync_date,
                                sync_batch_id=sync_batch_id,
                                api_status=ApiStatus.NOT_FOUND,
                                api_message=api_message,
                                old_values={
                                    "proclaimed_date": str(law.proclaimed_date) if law.proclaimed_date else None,
                                    "enforced_date": str(law.enforced_date) if law.enforced_date else None,
                                    "revision_type": law.revision_type,
                                },
                                new_values=None,
                                dept_name=law.dept_name,
                                dept_code=law.dept_code,
                            )
                            self.db.add(law_change)

                        yield {
                            "type": "changed",
                            "current": current,
                            "total": total_laws,
                            "law": not_found_law_info,
                            "message": f"[{current}/{total_laws}] {law_name} - 법령명 불일치",
                        }

                    yield {
                        "type": "progress",
                        "current": current,
                        "total": total_laws,
                        "law_name": law_name,
                        "status": "compared",
                        "result": compare_result,
                        "message": f"[{current}/{total_laws}] {law_name} - 비교 완료 ({compare_result})",
                    }

                    # Rate limiting
                    await asyncio.sleep(0.3)

                except asyncio.CancelledError:
                    # SSE 연결 끊김 등으로 인한 취소 — 진행 중 데이터 저장 후 종료
                    logger.warning(
                        "동기화 취소됨 (law=%s, %d/%d)", law_name, current, total_laws,
                    )
                    try:
                        await self.db.commit()
                    except Exception:
                        pass
                    raise
                except Exception as e:
                    logger.error(
                        "법령 동기화 오류 (law=%s): %s", law_name, e, exc_info=True,
                    )
                    failed += 1
                    yield {
                        "type": "error",
                        "current": current,
                        "total": total_laws,
                        "law_name": law_name,
                        "error": str(e),
                        "message": f"[{current}/{total_laws}] {law_name} - 오류: {str(e)}",
                    }

            await self.db.commit()

            # 자동 플래깅: 변경 감지된 법령에 연계된 조례의 revision_status를 "검토대기"로 설정
            flagged_count = 0
            if changed_laws:
                changed_law_ids = [cl["id"] for cl in changed_laws if cl.get("api_status") == "success"]
                if changed_law_ids:
                    flagged_count = await self._auto_flag_ordinances(changed_law_ids)

            yield {
                "type": "complete",
                "total": total_laws,
                "updated": updated,
                "failed": failed,
                "changed_count": len(changed_laws),
                "changed_laws": changed_laws,
                "flagged_ordinances": flagged_count,
                "message": (
                    f"동기화 완료: 총 {total_laws}건 중 {updated}건 성공, {failed}건 실패, "
                    f"{len(changed_laws)}건 변경, 검토대상 조례 {flagged_count}건 플래깅"
                ),
            }
        finally:
            await moleg_client.close()

    async def _auto_flag_ordinances(self, changed_law_ids: List[int]) -> int:
        """
        변경 감지된 법령에 연계된 조례를 자동으로 "검토대기" 상태로 설정

        - revision_status가 null인 조례: 항상 "검토대기"로 변경
        - revision_status가 "검토완료"인 조례: 새로운 법령 변경이 있을 때만 재플래그
          (법령 proclaimed_date != mapping.reviewed_law_date이면 새 변경)
        - "검토대기"/"검토중"/"개정확정" 상태인 조례는 덮어쓰지 않음
        """
        # 변경된 법령에 연계된 매핑 조회 (법령 정보 포함)
        mapping_stmt = (
            select(OrdinanceLawMapping)
            .options(selectinload(OrdinanceLawMapping.law))
            .where(OrdinanceLawMapping.law_id.in_(changed_law_ids))
        )
        mapping_result = await self.db.execute(mapping_stmt)
        mappings = mapping_result.scalars().all()

        if not mappings:
            return 0

        # 조례별로 새 변경이 있는지 판단
        ordinance_ids_to_flag: set = set()
        for mapping in mappings:
            if not mapping.law:
                continue
            # 이미 검토된 공포일과 동일하면 스킵 (같은 변경에 대한 재감지)
            if (
                mapping.reviewed_law_date
                and mapping.law.proclaimed_date
                and mapping.reviewed_law_date == mapping.law.proclaimed_date
            ):
                continue
            ordinance_ids_to_flag.add(mapping.ordinance_id)

        if not ordinance_ids_to_flag:
            return 0

        # revision_status가 null 또는 "검토완료"인 조례만 "검토대기"로 업데이트
        from sqlalchemy import or_
        ordinance_stmt = (
            select(Ordinance)
            .where(
                and_(
                    Ordinance.id.in_(list(ordinance_ids_to_flag)),
                    or_(
                        Ordinance.revision_status.is_(None),
                        Ordinance.revision_status == "검토완료",
                    ),
                )
            )
        )
        result = await self.db.execute(ordinance_stmt)
        ordinances = result.scalars().all()

        flagged = 0
        for ordinance in ordinances:
            ordinance.revision_status = "검토대기"
            flagged += 1

        if flagged > 0:
            await self.db.commit()

        return flagged
