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
        items = result.scalars().all()

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
                "law_id": m.law.id if m.law else None,
                "law_type": m.law.law_type if m.law else "",
                "law_name": m.law.law_name if m.law else "",
                "proclaimed_date": m.law.proclaimed_date if m.law else None,
                "enforced_date": m.law.enforced_date if m.law else None,
                "related_articles": m.related_articles,
            }
            for m in mappings
        ]

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

        # 법령명으로 법령 검색
        result = await self.db.execute(
            select(Law).where(Law.law_name == law_name)
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
        related_articles: Optional[str] = None,
    ) -> OrdinanceLawMapping:
        """조례-법령 매핑 수정"""
        result = await self.db.execute(
            select(OrdinanceLawMapping).where(OrdinanceLawMapping.id == mapping_id)
        )
        mapping = result.scalar_one_or_none()
        if not mapping:
            raise NotFoundError(f"Mapping {mapping_id} not found")

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
