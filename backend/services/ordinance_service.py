"""
Ordinance Service
"""
import os
import io
import asyncio
import httpx
import pandas as pd
from datetime import datetime, date
from typing import Optional, List
from fastapi import UploadFile
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.ordinance import Ordinance, OrdinanceArticle
from backend.models.law import Law
from backend.models.ordinance_law_mapping import OrdinanceLawMapping
from backend.core.exceptions import NotFoundError
from backend.external.moleg_client import MolegClient
from backend.services.law_sync_service import LawSyncService


class OrdinanceService:
    """Ordinance business logic"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_list(
        self,
        page: int = 1,
        size: int = 20,
        category: Optional[str] = None,
        department: Optional[str] = None,
        search: Optional[str] = None,
    ) -> dict:
        """Get paginated list of ordinances"""
        query = select(Ordinance).where(Ordinance.status == "ACTIVE")

        if category:
            query = query.where(Ordinance.category == category)
        if department:
            query = query.where(Ordinance.department == department)
        if search:
            query = query.where(Ordinance.name.ilike(f"%{search}%"))

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)

        # Paginate
        query = query.offset((page - 1) * size).limit(size)
        result = await self.db.execute(query)
        ordinances = result.scalars().all()

        # Add parent law count for each ordinance
        items = []
        for ordinance in ordinances:
            # Count parent laws
            parent_law_count = await self.db.scalar(
                select(func.count())
                .select_from(OrdinanceLawMapping)
                .where(OrdinanceLawMapping.ordinance_id == ordinance.id)
            ) or 0

            # Convert to dict and add count
            ordinance_dict = {
                "id": ordinance.id,
                "code": ordinance.code,
                "name": ordinance.name,
                "category": ordinance.category,
                "department": ordinance.department,
                "enacted_date": ordinance.enacted_date,
                "enforced_date": ordinance.enforced_date,
                "revision_date": ordinance.revision_date,
                "status": ordinance.status,
                "serial_no": ordinance.serial_no,
                "field_name": ordinance.field_name,
                "org_name": ordinance.org_name,
                "promulgation_no": ordinance.promulgation_no,
                "revision_type": ordinance.revision_type,
                "detail_link": ordinance.detail_link,
                "created_at": ordinance.created_at,
                "updated_at": ordinance.updated_at,
                "parent_law_count": parent_law_count,
            }
            items.append(ordinance_dict)

        return {
            "total": total,
            "page": page,
            "size": size,
            "items": items,
        }

    async def get_departments(self) -> List[dict]:
        """Get unique department list with count"""
        result = await self.db.execute(
            select(
                Ordinance.department,
                func.count(Ordinance.id).label('count')
            )
            .where(Ordinance.status == "ACTIVE")
            .where(Ordinance.department.isnot(None))
            .where(Ordinance.department != '')
            .group_by(Ordinance.department)
            .order_by(Ordinance.department)
        )
        rows = result.all()
        return [{"name": row[0], "count": row[1]} for row in rows]

    async def get_by_id(self, ordinance_id: int) -> Ordinance:
        """Get ordinance by ID"""
        result = await self.db.execute(
            select(Ordinance).where(Ordinance.id == ordinance_id)
        )
        ordinance = result.scalar_one_or_none()
        if not ordinance:
            raise NotFoundError(f"Ordinance {ordinance_id} not found")
        return ordinance

    async def get_articles(self, ordinance_id: int) -> List[OrdinanceArticle]:
        """Get ordinance articles"""
        await self.get_by_id(ordinance_id)  # Check exists
        result = await self.db.execute(
            select(OrdinanceArticle)
            .where(OrdinanceArticle.ordinance_id == ordinance_id)
            .order_by(OrdinanceArticle.article_no)
        )
        return result.scalars().all()

    async def get_parent_laws(self, ordinance_id: int) -> List[dict]:
        """Get parent laws mapped to ordinance (new structure)"""
        from sqlalchemy.orm import selectinload

        await self.get_by_id(ordinance_id)  # Check exists
        result = await self.db.execute(
            select(OrdinanceLawMapping)
            .options(selectinload(OrdinanceLawMapping.law))
            .where(OrdinanceLawMapping.ordinance_id == ordinance_id)
        )
        mappings = result.scalars().all()

        return [
            {
                "id": m.id,
                "law_id": m.law.law_id if m.law else None,
                "law_type": m.law.law_type if m.law else "",
                "law_name": m.law.law_name if m.law else "",
                "proclaimed_date": m.law.proclaimed_date if m.law else None,
                "enforced_date": m.law.enforced_date if m.law else None,
                "related_articles": m.related_articles,
            }
            for m in mappings
        ]

    async def _find_or_create_law(
        self,
        law_name: str,
        law_type: str,
        proclaimed_date: Optional[str] = None,
        enforced_date: Optional[str] = None,
    ) -> Law:
        """법령명과 법령유형으로 법령을 찾거나 생성"""
        # 법령명과 법령유형으로 법령 검색
        result = await self.db.execute(
            select(Law).where(
                and_(
                    Law.law_name == law_name,
                    Law.law_type == law_type
                )
            )
        )
        law = result.scalar_one_or_none()

        # 법령이 없으면 새로 생성
        if not law:
            # 다음 사용 가능한 law_serial_no와 law_id 찾기
            max_result = await self.db.execute(
                select(func.max(Law.law_serial_no), func.max(Law.law_id))
            )
            max_serial, max_law_id = max_result.one()
            next_serial = (max_serial or 0) + 1
            next_law_id = (max_law_id or 0) + 1

            # 날짜 변환
            proclaimed_date_obj = None
            enforced_date_obj = None
            if proclaimed_date:
                try:
                    proclaimed_date_obj = datetime.strptime(proclaimed_date, '%Y-%m-%d').date()
                except ValueError:
                    pass
            if enforced_date:
                try:
                    enforced_date_obj = datetime.strptime(enforced_date, '%Y-%m-%d').date()
                except ValueError:
                    pass

            # 새 법령 생성
            law = Law(
                law_serial_no=next_serial,
                law_id=next_law_id,
                law_name=law_name,
                law_type=law_type,
                proclaimed_date=proclaimed_date_obj,
                enforced_date=enforced_date_obj,
            )
            self.db.add(law)
            await self.db.flush()  # law.id를 얻기 위해 flush

        return law

    async def create_parent_law(
        self,
        ordinance_id: int,
        law_name: str,
        law_type: str,
        proclaimed_date: Optional[str] = None,
        enforced_date: Optional[str] = None,
        related_articles: Optional[str] = None,
    ) -> dict:
        """
        상위법령 추가 (프론트엔드 호환)

        법령이 없으면 자동으로 생성하고 매핑 생성
        """
        await self.get_by_id(ordinance_id)  # Check ordinance exists

        # 법령 찾기 또는 생성
        law = await self._find_or_create_law(
            law_name=law_name,
            law_type=law_type,
            proclaimed_date=proclaimed_date,
            enforced_date=enforced_date,
        )

        # 이미 매핑이 있는지 확인
        existing = await self.db.execute(
            select(OrdinanceLawMapping).where(
                and_(
                    OrdinanceLawMapping.ordinance_id == ordinance_id,
                    OrdinanceLawMapping.law_id == law.id
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"'{law_name}' 법령은 이미 매핑되어 있습니다.")

        # 매핑 생성
        mapping = OrdinanceLawMapping(
            ordinance_id=ordinance_id,
            law_id=law.id,
            related_articles=related_articles,
        )
        self.db.add(mapping)
        await self.db.commit()
        await self.db.refresh(mapping)

        return {
            "success": True,
            "id": mapping.id,
            "message": "상위법령이 추가되었습니다."
        }

    async def sync_from_moleg(self, org: str = "6110000", sborg: str = "3220000") -> dict:
        """
        법제처 API에서 자치법규 목록을 가져와 DB에 저장

        Args:
            org: 도/특별시/광역시 코드 (기본: 서울특별시)
            sborg: 시/군/구 코드 (기본: 강남구)

        Returns:
            동기화 결과 정보
        """
        api_key = os.getenv('MOLEG_API_KEY', 'test')
        base_url = "http://www.law.go.kr/DRF/lawSearch.do"

        all_ordinances = []
        page = 1
        max_display = 100

        params = {
            'OC': api_key,
            'target': 'ordin',
            'type': 'JSON',
            'display': max_display,
            'nw': 1,  # 현행
            'org': org,
            'sborg': sborg,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            while True:
                params['page'] = page
                response = await client.get(base_url, params=params)

                if response.text.strip().startswith('<!DOCTYPE'):
                    break

                data = response.json()
                ordin_search = data.get('OrdinSearch', {})

                if not ordin_search:
                    break

                total_count = int(ordin_search.get('totalCnt', 0))
                ordinances = ordin_search.get('law', [])

                if isinstance(ordinances, dict):
                    ordinances = [ordinances]

                if not ordinances:
                    break

                all_ordinances.extend(ordinances)

                if len(all_ordinances) >= total_count:
                    break

                page += 1
                await asyncio.sleep(0.3)

        # DB에 저장
        created = 0
        updated = 0

        for ordin_data in all_ordinances:
            ordin_id = ordin_data.get('자치법규ID')
            if not ordin_id:
                continue

            # 기존 데이터 조회
            result = await self.db.execute(
                select(Ordinance).where(Ordinance.code == ordin_id)
            )
            existing = result.scalar_one_or_none()

            # 날짜 파싱
            enacted_date = None
            enforced_date = None
            if ordin_data.get('공포일자'):
                try:
                    enacted_date = datetime.strptime(ordin_data['공포일자'], '%Y%m%d').date()
                except ValueError:
                    pass
            if ordin_data.get('시행일자'):
                try:
                    enforced_date = datetime.strptime(ordin_data['시행일자'], '%Y%m%d').date()
                except ValueError:
                    pass

            if existing:
                # 업데이트
                existing.name = ordin_data.get('자치법규명', existing.name)
                existing.category = ordin_data.get('자치법규종류', existing.category)
                existing.serial_no = ordin_data.get('자치법규일련번호')
                existing.field_name = ordin_data.get('자치법규분야명')
                existing.org_name = ordin_data.get('지자체기관명')
                existing.promulgation_no = ordin_data.get('공포번호')
                existing.revision_type = ordin_data.get('제개정구분명')
                existing.detail_link = ordin_data.get('자치법규상세링크')
                existing.enacted_date = enacted_date or existing.enacted_date
                existing.enforced_date = enforced_date or existing.enforced_date
                updated += 1
            else:
                # 신규 생성
                new_ordinance = Ordinance(
                    code=ordin_id,
                    name=ordin_data.get('자치법규명', ''),
                    category=ordin_data.get('자치법규종류'),
                    serial_no=ordin_data.get('자치법규일련번호'),
                    field_name=ordin_data.get('자치법규분야명'),
                    org_name=ordin_data.get('지자체기관명'),
                    promulgation_no=ordin_data.get('공포번호'),
                    revision_type=ordin_data.get('제개정구분명'),
                    detail_link=ordin_data.get('자치법규상세링크'),
                    enacted_date=enacted_date,
                    enforced_date=enforced_date,
                    status="ACTIVE",
                )
                self.db.add(new_ordinance)
                created += 1

        await self.db.commit()

        # 상위법령 동기화도 함께 수행
        parent_law_result = await self.sync_parent_laws(org, sborg)

        return {
            "success": True,
            "total_fetched": len(all_ordinances),
            "created": created,
            "updated": updated,
            "parent_laws": parent_law_result,
            "message": f"법제처 API 동기화 완료: {created}건 생성, {updated}건 갱신, 상위법령 {parent_law_result.get('created', 0)}건 매핑",
        }

    async def sync_parent_laws(self, org: str = "6110000", sborg: str = "3220000") -> dict:
        """
        lnkOrg API를 통해 상위법령 매핑 정보를 동기화 (새 구조 사용)

        Args:
            org: 도/특별시/광역시 코드
            sborg: 시/군/구 코드

        Returns:
            동기화 결과 정보
        """
        # LawSyncService 사용
        law_sync_service = LawSyncService(self.db)
        result = await law_sync_service.sync_from_lnk_org(sborg=sborg)

        return {
            "success": True,
            "total_fetched": result.get("total_items", 0),
            "created": result.get("synced_mappings", 0),
            "skipped": 0,
            "synced_laws": result.get("synced_laws", 0),
        }

    def _infer_law_type(self, law_name: str) -> str:
        """법령명에서 유형 추론"""
        if "시행규칙" in law_name:
            return "시행규칙"
        elif "시행령" in law_name:
            return "시행령"
        else:
            return "법률"

    async def upload_from_excel(self, file: UploadFile) -> dict:
        """
        엑셀 파일에서 소관부서 정보를 읽어 DB 업데이트

        엑셀 형식:
        순번 | 법규명 | 제·개정일 | 제·개정구분 | 법규구분 | 소관부서

        Args:
            file: 업로드된 엑셀 파일

        Returns:
            업로드 결과 정보
        """
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))

        # 컬럼명 정규화
        df.columns = df.columns.str.strip()

        def normalize_text(s: str) -> str:
            """
            특수문자 정규화
            - ㆍ (U+318D, 한글 자모 중점) -> · (U+00B7, 가운뎃점)
            - ･ (U+FF65, 반각 가운뎃점) -> · (U+00B7, 가운뎃점)
            """
            return s.replace('ㆍ', '·').replace('･', '·').strip()

        updated = 0
        not_found = 0

        for _, row in df.iterrows():
            name = normalize_text(str(row.get('법규명', '')))
            department = normalize_text(str(row.get('소관부서', '')))

            if not name or not department:
                continue

            # 법규명으로 검색 (DB의 이름도 정규화하여 비교)
            result = await self.db.execute(
                select(Ordinance)
            )
            ordinances = result.scalars().all()

            ordinance = None
            for ord_item in ordinances:
                if normalize_text(ord_item.name) == name:
                    ordinance = ord_item
                    break

            if ordinance:
                ordinance.department = department
                updated += 1
            else:
                not_found += 1

        await self.db.commit()

        return {
            "success": True,
            "total_rows": len(df),
            "updated": updated,
            "not_found": not_found,
            "message": f"엑셀 업로드 완료: {updated}건 업데이트, {not_found}건 미발견",
        }

    # ========== 조례-법령 매핑 CRUD (새 구조) ==========

    async def create_law_mapping(
        self,
        ordinance_id: int,
        law_id: int,
        related_articles: Optional[str] = None,
    ) -> OrdinanceLawMapping:
        """조례-법령 매핑 추가"""
        await self.get_by_id(ordinance_id)  # Check exists

        # Law 존재 확인
        law_result = await self.db.execute(
            select(Law).where(Law.id == law_id)
        )
        law = law_result.scalar_one_or_none()
        if not law:
            raise NotFoundError(f"Law {law_id} not found")

        # 중복 체크
        existing = await self.db.execute(
            select(OrdinanceLawMapping).where(
                and_(
                    OrdinanceLawMapping.ordinance_id == ordinance_id,
                    OrdinanceLawMapping.law_id == law_id
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"이미 매핑된 상위법령입니다: {law.law_name}")

        mapping = OrdinanceLawMapping(
            ordinance_id=ordinance_id,
            law_id=law_id,
            related_articles=related_articles,
        )
        self.db.add(mapping)
        await self.db.commit()
        await self.db.refresh(mapping)
        return mapping

    async def update_law_mapping(
        self,
        mapping_id: int,
        law_name: Optional[str] = None,
        law_type: Optional[str] = None,
        proclaimed_date: Optional[str] = None,
        enforced_date: Optional[str] = None,
        related_articles: Optional[str] = None,
    ) -> OrdinanceLawMapping:
        """조례-법령 매핑 수정"""
        result = await self.db.execute(
            select(OrdinanceLawMapping).where(OrdinanceLawMapping.id == mapping_id)
        )
        mapping = result.scalar_one_or_none()
        if not mapping:
            raise NotFoundError(f"Mapping {mapping_id} not found")

        # If law information is being changed, find or create new Law
        if law_name is not None or law_type is not None:
            # Find or create the law
            law = await self._find_or_create_law(
                law_name=law_name or "",
                law_type=law_type or "법률",
                proclaimed_date=proclaimed_date,
                enforced_date=enforced_date,
            )
            # Update mapping to point to new law
            mapping.law_id = law.id

        # Update related articles
        if related_articles is not None:
            mapping.related_articles = related_articles

        await self.db.commit()
        await self.db.refresh(mapping)
        return mapping

    async def delete_law_mapping(self, mapping_id: int) -> bool:
        """조례-법령 매핑 삭제"""
        result = await self.db.execute(
            select(OrdinanceLawMapping).where(OrdinanceLawMapping.id == mapping_id)
        )
        mapping = result.scalar_one_or_none()
        if not mapping:
            raise NotFoundError(f"Mapping {mapping_id} not found")

        await self.db.delete(mapping)
        await self.db.commit()
        return True

    async def create_ordinance(
        self,
        name: str,
        category: str = "조례",
        department: Optional[str] = None,
        enacted_date: Optional[str] = None,
        enforced_date: Optional[str] = None,
    ) -> dict:
        """
        자치법규 수동 등록

        Args:
            name: 자치법규명
            category: 자치법규종류 (조례/규칙)
            department: 소관부서
            enacted_date: 공포일자 (YYYY-MM-DD)
            enforced_date: 시행일자 (YYYY-MM-DD)

        Returns:
            등록 결과 정보
        """
        import uuid

        # 동일한 이름의 자치법규가 있는지 확인
        existing = await self.db.execute(
            select(Ordinance).where(Ordinance.name == name)
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"'{name}' 자치법규가 이미 존재합니다.")

        # 날짜 변환
        enacted_date_obj = None
        enforced_date_obj = None
        if enacted_date:
            try:
                enacted_date_obj = datetime.strptime(enacted_date, '%Y-%m-%d').date()
            except ValueError:
                pass
        if enforced_date:
            try:
                enforced_date_obj = datetime.strptime(enforced_date, '%Y-%m-%d').date()
            except ValueError:
                pass

        # 수동 등록용 고유 코드 생성 (UUID 사용)
        manual_code = f"MANUAL-{uuid.uuid4().hex[:12].upper()}"

        # 자치법규 생성
        ordinance = Ordinance(
            code=manual_code,
            name=name,
            category=category,
            department=department,
            enacted_date=enacted_date_obj,
            enforced_date=enforced_date_obj,
            revision_type="수동등록",
            status="ACTIVE",
        )
        self.db.add(ordinance)
        await self.db.commit()
        await self.db.refresh(ordinance)

        return {
            "success": True,
            "id": ordinance.id,
            "message": f"'{name}' 자치법규가 등록되었습니다.",
        }

    async def register_from_api(
        self,
        serial_no: str,
        name: str,
        ordinance_id: str,
        enacted_date: Optional[str] = None,
        promulgation_no: Optional[str] = None,
        revision_type: Optional[str] = None,
        org_name: Optional[str] = None,
        category: Optional[str] = None,
        enforced_date: Optional[str] = None,
        detail_link: Optional[str] = None,
        field_name: Optional[str] = None,
        department: Optional[str] = None,
    ) -> dict:
        """
        법제처 API 검색 결과로 자치법규 등록

        Args:
            serial_no: 자치법규일련번호
            name: 자치법규명
            ordinance_id: 자치법규ID (code로 사용)
            enacted_date: 공포일자 (YYYYMMDD)
            promulgation_no: 공포번호
            revision_type: 제개정구분명
            org_name: 지자체기관명
            category: 자치법규종류
            enforced_date: 시행일자 (YYYYMMDD)
            detail_link: 자치법규상세링크
            field_name: 자치법규분야명
            department: 소관부서 (수동 입력)

        Returns:
            등록 결과 정보
        """
        # 이미 등록된 자치법규인지 확인 (code로 확인)
        existing = await self.db.execute(
            select(Ordinance).where(Ordinance.code == ordinance_id)
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"'{name}' 자치법규가 이미 등록되어 있습니다. (ID: {ordinance_id})")

        # 날짜 변환 (YYYYMMDD -> date)
        enacted_date_obj = None
        enforced_date_obj = None
        if enacted_date:
            try:
                enacted_date_obj = datetime.strptime(enacted_date, '%Y%m%d').date()
            except ValueError:
                pass
        if enforced_date:
            try:
                enforced_date_obj = datetime.strptime(enforced_date, '%Y%m%d').date()
            except ValueError:
                pass

        # 자치법규 생성
        ordinance = Ordinance(
            code=ordinance_id,
            name=name,
            category=category,
            department=department,
            enacted_date=enacted_date_obj,
            enforced_date=enforced_date_obj,
            serial_no=serial_no,
            field_name=field_name,
            org_name=org_name,
            promulgation_no=promulgation_no,
            revision_type=revision_type,
            detail_link=detail_link,
            status="ACTIVE",
        )
        self.db.add(ordinance)
        await self.db.commit()
        await self.db.refresh(ordinance)

        return {
            "success": True,
            "id": ordinance.id,
            "message": f"'{name}' 자치법규가 등록되었습니다.",
        }

    async def update_all_ordinance_info(
        self,
        org: str = "6110000",
        sborg: str = "3220000",
    ) -> dict:
        """
        모든 자치법규 정보를 법제처 API로 업데이트

        Args:
            org: 도/특별시/광역시 코드
            sborg: 시/군/구 코드

        Returns:
            {"total_ordinances": 전체 수, "updated": 업데이트 수, "failed": 실패 수}
        """
        import httpx
        from backend.core.config import settings

        api_key = settings.MOLEG_API_KEY or "test"
        url = "http://www.law.go.kr/DRF/lawSearch.do"

        # 모든 자치법규 조회
        stmt = select(Ordinance).where(Ordinance.status == "ACTIVE")
        result = await self.db.execute(stmt)
        all_ordinances = list(result.scalars().all())

        total_ordinances = len(all_ordinances)
        updated = 0
        failed = 0

        async with httpx.AsyncClient(timeout=30.0) as client:
            for ordinance in all_ordinances:
                try:
                    # 자치법규명으로 API 검색
                    response = await client.get(
                        url,
                        params={
                            "OC": api_key,
                            "target": "ordin",
                            "type": "JSON",
                            "query": f'"{ordinance.name}"',  # 정확한 검색
                            "org": org,
                            "sborg": sborg,
                            "display": 10,
                            "nw": 1,
                        },
                    )

                    if response.text.strip().startswith("<!DOCTYPE"):
                        failed += 1
                        continue

                    data = response.json()
                    ordin_search = data.get("OrdinSearch", {})

                    if not ordin_search:
                        failed += 1
                        continue

                    items = ordin_search.get("law", [])
                    if isinstance(items, dict):
                        items = [items]

                    # 정확히 일치하는 자치법규명 찾기
                    exact_match = None
                    for item in items:
                        if item.get("자치법규명") == ordinance.name:
                            exact_match = item
                            break

                    if exact_match:
                        # 정보 업데이트
                        ordinance.code = exact_match.get("자치법규ID", ordinance.code)
                        ordinance.serial_no = exact_match.get("자치법규일련번호")
                        ordinance.promulgation_no = exact_match.get("공포번호")
                        ordinance.revision_type = exact_match.get("제개정구분명")
                        ordinance.org_name = exact_match.get("지자체기관명")
                        ordinance.category = exact_match.get("자치법규종류", ordinance.category)
                        ordinance.detail_link = exact_match.get("자치법규상세링크")
                        ordinance.field_name = exact_match.get("자치법규분야명")

                        # 날짜 업데이트
                        if exact_match.get("공포일자"):
                            try:
                                ordinance.enacted_date = datetime.strptime(
                                    exact_match["공포일자"], '%Y%m%d'
                                ).date()
                            except ValueError:
                                pass
                        if exact_match.get("시행일자"):
                            try:
                                ordinance.enforced_date = datetime.strptime(
                                    exact_match["시행일자"], '%Y%m%d'
                                ).date()
                            except ValueError:
                                pass

                        updated += 1
                    else:
                        failed += 1

                    # Rate limiting
                    await asyncio.sleep(0.3)

                except Exception as e:
                    print(f"Failed to update ordinance '{ordinance.name}': {e}")
                    failed += 1

        await self.db.commit()

        return {
            "total_ordinances": total_ordinances,
            "updated": updated,
            "failed": failed,
        }
