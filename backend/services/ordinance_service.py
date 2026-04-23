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
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.ordinance import Ordinance
from backend.models.department import Department
from backend.models.law import Law
from backend.models.ordinance_law_mapping import OrdinanceLawMapping
from backend.models.ordinance_review import OrdinanceReview
from backend.models.revision_detection_result import RevisionDetectionResult
from backend.core.exceptions import NotFoundError
from backend.schemas.ordinance import OrdinanceReviewCreate, OrdinanceReviewUpdate
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
        department_id: Optional[int] = None,
        search: Optional[str] = None,
        no_parent_law_filter: Optional[str] = None,
        needs_revision_filter: Optional[str] = None,
        revision_type: Optional[str] = None,
        exclude_other_law_revision: bool = False,
        review_result_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
        revision_status_filter: Optional[str] = None,  # "any" | "검토대기" | "검토중" | "개정확정"
    ) -> dict:
        """Get paginated list of ordinances"""
        from backend.models.department import Department as DeptModel

        query = select(Ordinance)
        if status_filter:
            query = query.where(Ordinance.status == status_filter)
        else:
            query = query.where(Ordinance.status == "ACTIVE")

        if category:
            query = query.where(Ordinance.category == category)
        if department_id:
            # 부서 마스터 ID로 부서명 조회 후 문자열 기반 필터
            dept_result = await self.db.execute(
                select(DeptModel).where(DeptModel.id == department_id)
            )
            dept = dept_result.scalar_one_or_none()
            if dept:
                # 해당 부서 + 하위 부서의 이름 패턴 수집
                name_candidates = set()
                if dept.parent_name:
                    # 하위 부서 (과): "행정국 총무과" 형태
                    name_candidates.add(f"{dept.parent_name} {dept.name}")
                else:
                    # 상위 부서 (국/실): 자신 + 산하 과 전부
                    name_candidates.add(dept.name)
                    child_result = await self.db.execute(
                        select(DeptModel.name).where(DeptModel.parent_name == dept.name)
                    )
                    for (child_name,) in child_result:
                        name_candidates.add(f"{dept.name} {child_name}")

                query = query.where(Ordinance.department.in_(list(name_candidates)))
        elif department:
            # 레거시: 문자열 기반 부서 필터
            query = query.where(
                (Ordinance.department == department) |
                (Ordinance.department.like(f"% {department}")) |
                (Ordinance.department.like(f"{department} %"))
            )
        if search:
            query = query.where(Ordinance.name.ilike(f"%{search}%"))
        if revision_type:
            # 상위법령(Law)의 제개정구분으로 필터링
            revision_type_subquery = (
                select(OrdinanceLawMapping.ordinance_id)
                .join(Law, OrdinanceLawMapping.law_id == Law.id)
                .where(Law.revision_type == revision_type)
                .distinct()
            )
            query = query.where(Ordinance.id.in_(revision_type_subquery))

        # 상위법령 필터
        if no_parent_law_filter == "connected":
            # 상위법령 매핑이 있는 조례
            subquery = select(OrdinanceLawMapping.ordinance_id).distinct()
            query = query.where(Ordinance.id.in_(subquery))
        elif no_parent_law_filter == "no_mapping":
            # 상위법령 매핑이 없고, no_parent_law가 False인 조례
            subquery = select(OrdinanceLawMapping.ordinance_id).distinct()
            query = query.where(
                and_(
                    Ordinance.id.notin_(subquery),
                    Ordinance.no_parent_law == False
                )
            )
        elif no_parent_law_filter == "confirmed_none":
            # 상위법령 없음으로 확인된 조례
            query = query.where(Ordinance.no_parent_law == True)

        # 개정대상 필터
        # 로직: 2단계(승인된 검토의견)가 있으면 최종값, 없으면 1단계(자동판별) 사용
        # 여러 법령 중 하나라도 "개정필요"면 전체 "개정필요"
        if needs_revision_filter:
            has_mapping_subquery = select(OrdinanceLawMapping.ordinance_id).distinct()

            # 승인된 "개정필요" 검토가 있는 조례 (하나라도 있으면 개정필요)
            approved_revision_needed_subquery = (
                select(OrdinanceReview.ordinance_id)
                .where(OrdinanceReview.approval_status == "approved")
                .where(OrdinanceReview.review_result == "개정필요")
                .distinct()
            )
            # 승인된 검토가 존재하는 조례
            has_approved_review_subquery = (
                select(OrdinanceReview.ordinance_id)
                .where(OrdinanceReview.approval_status == "approved")
                .distinct()
            )

            # 1단계 자동판별: 판별 결과 또는 시행일 비교
            detection_revision_subquery = (
                select(RevisionDetectionResult.ordinance_id)
                .where(RevisionDetectionResult.needs_revision == True)
                .distinct()
            )
            has_detection_subquery = (
                select(RevisionDetectionResult.ordinance_id).distinct()
            )
            fallback_revision_subquery = (
                select(OrdinanceLawMapping.ordinance_id)
                .join(Law, OrdinanceLawMapping.law_id == Law.id)
                .where(Law.enforced_date.isnot(None))
            )
            if exclude_other_law_revision:
                fallback_revision_subquery = fallback_revision_subquery.where(Law.revision_type != '타법개정')
            fallback_revision_subquery = (
                fallback_revision_subquery
                .group_by(OrdinanceLawMapping.ordinance_id)
                .having(func.max(Law.enforced_date) > Ordinance.enacted_date)
            )

            if needs_revision_filter == "needs_revision":
                query = query.where(
                    Ordinance.id.in_(has_mapping_subquery),
                    or_(
                        # 2단계: 승인된 검토 중 하나라도 "개정필요"
                        Ordinance.id.in_(approved_revision_needed_subquery),
                        # 1단계: 승인된 검토 없고, 자동판별이 개정필요
                        and_(
                            Ordinance.id.notin_(has_approved_review_subquery),
                            or_(
                                Ordinance.id.in_(detection_revision_subquery),
                                and_(
                                    Ordinance.id.notin_(has_detection_subquery),
                                    Ordinance.enacted_date.isnot(None),
                                    Ordinance.id.in_(fallback_revision_subquery),
                                ),
                            ),
                        ),
                    ),
                )
            elif needs_revision_filter == "no_revision":
                query = query.where(
                    Ordinance.id.in_(has_mapping_subquery),
                    or_(
                        # 2단계: 승인된 검토가 있고, 모두 "개정불필요"
                        and_(
                            Ordinance.id.in_(has_approved_review_subquery),
                            Ordinance.id.notin_(approved_revision_needed_subquery),
                        ),
                        # 1단계: 승인된 검토 없고, 자동판별이 개정불필요
                        and_(
                            Ordinance.id.notin_(has_approved_review_subquery),
                            or_(
                                and_(
                                    Ordinance.id.in_(has_detection_subquery),
                                    Ordinance.id.notin_(detection_revision_subquery),
                                ),
                                and_(
                                    Ordinance.id.notin_(has_detection_subquery),
                                    Ordinance.enacted_date.isnot(None),
                                    Ordinance.id.notin_(fallback_revision_subquery),
                                ),
                            ),
                        ),
                    ),
                )

        # 검토 상태 필터 (revision_status 컬럼 기반)
        if revision_status_filter:
            if revision_status_filter == "any":
                # revision_status가 설정된 조례 (검토대기/검토중/개정확정)
                query = query.where(Ordinance.revision_status.isnot(None))
            else:
                query = query.where(Ordinance.revision_status == revision_status_filter)

        # 검토결과 필터
        if review_result_filter:
            if review_result_filter == "미검토":
                # 검토이력이 없는 조례
                has_review_subquery = select(OrdinanceReview.ordinance_id).distinct()
                query = query.where(Ordinance.id.notin_(has_review_subquery))
            else:
                # 최신 검토결과가 해당 값인 조례
                latest_review_subquery = (
                    select(
                        OrdinanceReview.ordinance_id,
                        func.max(OrdinanceReview.created_at).label("max_created")
                    )
                    .group_by(OrdinanceReview.ordinance_id)
                    .subquery()
                )
                latest_review_join = (
                    select(OrdinanceReview.ordinance_id, OrdinanceReview.review_result, OrdinanceReview.approval_status)
                    .join(
                        latest_review_subquery,
                        and_(
                            OrdinanceReview.ordinance_id == latest_review_subquery.c.ordinance_id,
                            OrdinanceReview.created_at == latest_review_subquery.c.max_created,
                        )
                    )
                )
                if review_result_filter == "반려":
                    matched_subquery = latest_review_join.where(OrdinanceReview.approval_status == "rejected")
                else:
                    matched_subquery = latest_review_join.where(OrdinanceReview.review_result == review_result_filter)
                query = query.where(Ordinance.id.in_(select(matched_subquery.subquery().c.ordinance_id)))

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)

        # Paginate
        query = query.offset((page - 1) * size).limit(size)
        result = await self.db.execute(query)
        ordinances = result.scalars().all()

        # Add parent law count and needs_revision for each ordinance
        items = []
        for ordinance in ordinances:
            # Count parent laws
            parent_law_count = await self.db.scalar(
                select(func.count())
                .select_from(OrdinanceLawMapping)
                .where(OrdinanceLawMapping.ordinance_id == ordinance.id)
            ) or 0

            # 상위법령 제개정구분 목록 조회
            law_revision_types_result = await self.db.execute(
                select(Law.revision_type)
                .select_from(OrdinanceLawMapping)
                .join(Law, OrdinanceLawMapping.law_id == Law.id)
                .where(OrdinanceLawMapping.ordinance_id == ordinance.id)
                .where(Law.revision_type.isnot(None))
                .where(Law.revision_type != '')
                .distinct()
            )
            law_revision_types = [row[0] for row in law_revision_types_result.all()]

            # === 1단계: 자동판별 (시스템 일자 비교) ===
            needs_revision = None
            if parent_law_count > 0:
                detection_count = await self.db.scalar(
                    select(func.count())
                    .select_from(RevisionDetectionResult)
                    .where(RevisionDetectionResult.ordinance_id == ordinance.id)
                ) or 0
                if detection_count > 0:
                    # 판별 결과 존재: 하나라도 needs_revision=True이면 개정필요
                    has_revision = await self.db.scalar(
                        select(func.count())
                        .select_from(RevisionDetectionResult)
                        .where(RevisionDetectionResult.ordinance_id == ordinance.id)
                        .where(RevisionDetectionResult.needs_revision == True)
                    ) or 0
                    needs_revision = 1 if has_revision > 0 else 0
                elif ordinance.enacted_date:
                    # 판별 결과 없음: 시행일 비교로 폴백
                    enforced_query = (
                        select(func.max(Law.enforced_date))
                        .select_from(OrdinanceLawMapping)
                        .join(Law, OrdinanceLawMapping.law_id == Law.id)
                        .where(OrdinanceLawMapping.ordinance_id == ordinance.id)
                        .where(Law.enforced_date.isnot(None))
                    )
                    if exclude_other_law_revision:
                        enforced_query = enforced_query.where(Law.revision_type != '타법개정')
                    max_enforced_date = await self.db.scalar(enforced_query)
                    if max_enforced_date:
                        needs_revision = 1 if max_enforced_date > ordinance.enacted_date else 0

            # === 2단계: 검토의견 (AI분석→담당자검토→관리자승인) ===
            # 승인된 검토의견이 있으면 2단계가 최종값
            # 여러 법령에 대한 검토 중 하나라도 "개정필요"면 전체 "개정필요"
            latest_review_result = None
            latest_approval_status = None
            review_rows = (await self.db.execute(
                select(OrdinanceReview.review_result, OrdinanceReview.approval_status)
                .where(OrdinanceReview.ordinance_id == ordinance.id)
                .order_by(OrdinanceReview.created_at.desc())
            )).all()
            if review_rows:
                if review_rows[0].approval_status == "rejected":
                    latest_review_result = "반려"
                    latest_approval_status = "rejected"
                else:
                    approved_results = [
                        r.review_result for r in review_rows
                        if r.approval_status == "approved"
                    ]
                    if any(r == "개정필요" for r in approved_results):
                        latest_review_result = "개정필요"
                        latest_approval_status = "approved"
                    elif approved_results:
                        latest_review_result = approved_results[0]
                        latest_approval_status = "approved"
                    else:
                        latest_review_result = review_rows[0].review_result
                        latest_approval_status = review_rows[0].approval_status

            # 2단계 결과가 있으면 1단계를 오버라이드 (최종값)
            if latest_approval_status == "approved":
                if latest_review_result == "개정불필요":
                    needs_revision = 0  # 초록불 (관리자 승인)
                elif latest_review_result == "개정필요":
                    needs_revision = 2  # 빨강불 (관리자 승인)
            elif latest_review_result in ("개정불필요", "개정필요"):
                needs_revision = 3  # 주황불 오각형 (담당자 제출, 관리자 미승인)

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
                "no_parent_law": ordinance.no_parent_law,
                "needs_revision": needs_revision,
                "law_revision_types": law_revision_types,
                "revision_status": ordinance.revision_status,
                "latest_review_result": latest_review_result,
            }
            items.append(ordinance_dict)

        return {
            "total": total,
            "page": page,
            "size": size,
            "items": items,
        }

    async def set_no_parent_law(self, ordinance_id: int, value: bool) -> dict:
        """상위법령 없음 설정/해제"""
        ordinance = await self.get_by_id(ordinance_id)
        ordinance.no_parent_law = value
        await self.db.commit()
        await self.db.refresh(ordinance)

        if value:
            return {"success": True, "message": "상위법령 없음으로 설정되었습니다."}
        else:
            return {"success": True, "message": "상위법령 없음 설정이 해제되었습니다."}

    async def get_departments(self) -> List[dict]:
        """Get unique department list with count, ordered by sort_order"""
        result = await self.db.execute(
            select(
                Ordinance.department,
                func.count(Ordinance.id).label('count'),
                func.coalesce(Department.sort_order, 9999).label('sort_order')
            )
            .outerjoin(Department, Ordinance.department == Department.name)
            .where(Ordinance.status == "ACTIVE")
            .where(Ordinance.department.isnot(None))
            .where(Ordinance.department != '')
            .group_by(Ordinance.department, Department.sort_order)
            .order_by(func.coalesce(Department.sort_order, 9999), Ordinance.department)
        )
        rows = result.all()
        return [{"name": row[0], "count": row[1]} for row in rows]

    async def get_revision_types(self) -> List[dict]:
        """상위법령의 제개정구분 목록 조회 (드롭다운용)"""
        result = await self.db.execute(
            select(
                Law.revision_type,
                func.count(func.distinct(OrdinanceLawMapping.ordinance_id)).label('count')
            )
            .join(OrdinanceLawMapping, OrdinanceLawMapping.law_id == Law.id)
            .join(Ordinance, OrdinanceLawMapping.ordinance_id == Ordinance.id)
            .where(Ordinance.status == "ACTIVE")
            .where(Law.revision_type.isnot(None))
            .where(Law.revision_type != '')
            .group_by(Law.revision_type)
            .order_by(func.count(func.distinct(OrdinanceLawMapping.ordinance_id)).desc())
        )
        rows = result.all()
        return [{"revision_type": row[0], "count": row[1]} for row in rows]

    async def get_by_id(self, ordinance_id: int) -> Ordinance:
        """Get ordinance by ID"""
        result = await self.db.execute(
            select(Ordinance).where(Ordinance.id == ordinance_id)
        )
        ordinance = result.scalar_one_or_none()
        if not ordinance:
            raise NotFoundError(f"조례를 찾을 수 없습니다 (ID: {ordinance_id})")
        return ordinance

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
                "law_internal_id": m.law.id if m.law else None,  # Law 테이블 PK (연계 조례 조회용)
                "law_id": m.law.law_id if m.law else None,
                "law_type": m.law.law_type if m.law else "",
                "law_name": m.law.law_name if m.law else "",
                "proclaimed_date": m.law.proclaimed_date if m.law else None,
                "enforced_date": m.law.enforced_date if m.law else None,
                "revision_type": m.law.revision_type if m.law else None,
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
        """법령명과 법령유형으로 법령을 찾거나 생성 (법제처 API 자동 조회 포함)"""
        from backend.utils.text import normalize_name, normalize_name_for_compare
        from backend.core.config import settings
        import logging

        logger = logging.getLogger(__name__)
        law_name = normalize_name(law_name)

        # 법령명으로 DB 검색 (법령유형은 프론트/법제처 간 명칭 차이가 있으므로 제외)
        result = await self.db.execute(
            select(Law).where(Law.law_name == law_name).limit(1)
        )
        law = result.scalar_one_or_none()

        if law:
            return law

        # DB에 없으면 법제처 API로 실제 법령 정보 조회
        api_result = await self._search_law_from_api(law_name)

        if api_result:
            # 이름 표기 차이로 인한 중복 방지 — DB UNIQUE 제약 모두 사전 체크:
            #   laws.law_id         UNIQUE  (법령 단위 고유키)
            #   laws.law_serial_no  UNIQUE  (ix_laws_law_serial_no; 개정 단위 MST)
            # 둘 중 하나라도 DB에 이미 있으면 그 row를 재사용해 새 row를 만들지 않음.
            if api_result.law_id:
                existing = (await self.db.execute(
                    select(Law).where(Law.law_id == api_result.law_id).limit(1)
                )).scalar_one_or_none()
                if existing:
                    logger.info(
                        "중복 방지(law_id 일치): 입력 '%s' → law_id=%d 기존 row(id=%d, '%s') 재사용",
                        law_name, api_result.law_id, existing.id, existing.law_name,
                    )
                    return existing

            if api_result.law_serial_no:
                existing = (await self.db.execute(
                    select(Law).where(Law.law_serial_no == api_result.law_serial_no).limit(1)
                )).scalar_one_or_none()
                if existing:
                    logger.info(
                        "중복 방지(law_serial_no 일치): 입력 '%s' → law_serial_no=%d 기존 row(id=%d, '%s') 재사용",
                        law_name, api_result.law_serial_no, existing.id, existing.law_name,
                    )
                    return existing

            # 법제처 API 결과로 정확한 정보의 법령 생성
            law = Law(
                law_serial_no=api_result.law_serial_no,
                law_id=api_result.law_id,
                law_name=api_result.law_name,
                law_abbr=api_result.law_abbr,
                law_type=api_result.law_type or law_type,
                proclaimed_date=api_result.proclaimed_date,
                proclaimed_no=api_result.proclaimed_no,
                enforced_date=api_result.enforced_date,
                revision_type=api_result.revision_type,
                history_code=api_result.history_code,
                dept_name=api_result.dept_name,
                dept_code=api_result.dept_code,
                detail_link=api_result.detail_link,
                last_synced_at=datetime.utcnow(),
            )
            logger.info(
                "법제처 API에서 법령 조회 성공: %s (law_id=%d, MST=%d)",
                api_result.law_name, api_result.law_id, api_result.law_serial_no,
            )
        else:
            # 법제처에서 못 찾으면 placeholder 생성 (수동 등록 케이스)
            max_result = await self.db.execute(
                select(func.max(Law.law_serial_no), func.max(Law.law_id))
            )
            max_serial, max_law_id = max_result.one()
            next_serial = (max_serial or 0) + 1
            next_law_id = (max_law_id or 0) + 1

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

            law = Law(
                law_serial_no=next_serial,
                law_id=next_law_id,
                law_name=law_name,
                law_type=law_type,
                proclaimed_date=proclaimed_date_obj,
                enforced_date=enforced_date_obj,
            )
            logger.warning(
                "법제처 API에서 법령 미발견, placeholder 생성: %s (law_id=%d)",
                law_name, next_law_id,
            )

        self.db.add(law)
        await self.db.flush()
        return law

    async def _search_law_from_api(
        self,
        law_name: str,
    ):
        """법제처 API에서 법령명으로 검색하여 정확히 일치하는 결과 반환"""
        from backend.utils.text import normalize_name_for_compare
        from backend.services.law_sync_service import LawSyncService, LawSearchResult
        import logging

        logger = logging.getLogger(__name__)

        try:
            sync_service = LawSyncService(self.db)
            target_normalized = normalize_name_for_compare(law_name)

            # 1) 현행법령 검색
            results, _ = await sync_service.search_laws(query=law_name, display=30)
            match = self._find_api_match(results, law_name, target_normalized)
            if match:
                return match

            # 2) 시행예정 포함 검색 (nw=2 fallback)
            results, _ = await sync_service.search_laws(query=law_name, display=30, nw=2)
            match = self._find_api_match(results, law_name, target_normalized)
            if match:
                return match

        except Exception as e:
            logger.warning("법제처 API 조회 실패 (법령명=%s): %s", law_name, e)

        return None

    @staticmethod
    def _find_api_match(results, law_name: str, target_normalized: str):
        """검색 결과에서 정확히 일치하는 법령 찾기"""
        from backend.utils.text import normalize_name_for_compare

        # 완전 일치 우선
        for item in results:
            if item.law_name == law_name:
                return item

        # 정규화 비교
        for item in results:
            if normalize_name_for_compare(item.law_name) == target_normalized:
                return item

        return None

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

        # no_parent_law 플래그 자동 해제 (FR-006a)
        ordinance = await self.get_by_id(ordinance_id)
        if ordinance.no_parent_law:
            ordinance.no_parent_law = False

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

            from backend.utils.text import normalize_name
            if existing:
                # EXCLUDED 상태인 조례는 스킵
                if existing.status == "EXCLUDED":
                    continue
                # 업데이트
                existing.name = normalize_name(ordin_data.get('자치법규명', '')) or existing.name
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
                    name=normalize_name(ordin_data.get('자치법규명', '')),
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

        # 폐지 감지: API 응답에 없는 ACTIVE 조례를 ABOLISHED 처리 (소프트 삭제)
        abolished = 0
        api_codes = {ordin.get('자치법규ID') for ordin in all_ordinances if ordin.get('자치법규ID')}
        if api_codes:
            active_result = await self.db.execute(
                select(Ordinance).where(
                    and_(
                        Ordinance.status == "ACTIVE",
                        Ordinance.code.notin_(api_codes),
                    )
                )
            )
            for ord_to_abolish in active_result.scalars().all():
                ord_to_abolish.status = "ABOLISHED"
                abolished += 1

        await self.db.commit()

        # 상위법령 동기화도 함께 수행
        parent_law_result = await self.sync_parent_laws(org, sborg)

        return {
            "success": True,
            "total_fetched": len(all_ordinances),
            "created": created,
            "updated": updated,
            "abolished": abolished,
            "parent_laws": parent_law_result,
            "message": f"법제처 API 동기화 완료: {created}건 생성, {updated}건 갱신, {abolished}건 폐지, 상위법령 {parent_law_result.get('created', 0)}건 매핑",
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
            """특수문자 정규화 — 법제처 기준 ㆍ(U+318D)로 통일"""
            from backend.utils.text import normalize_name
            return normalize_name(s)

        updated = 0
        not_found = 0
        excluded = 0

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
                # 의회사무국 소속 조례는 자동 EXCLUDED 처리
                if department == "의회사무국":
                    ordinance.status = "EXCLUDED"
                    excluded += 1
                updated += 1
            else:
                not_found += 1

        await self.db.commit()

        excluded_msg = f", {excluded}건 제외(의회사무국)" if excluded else ""
        return {
            "success": True,
            "total_rows": len(df),
            "updated": updated,
            "not_found": not_found,
            "excluded": excluded,
            "message": f"엑셀 업로드 완료: {updated}건 업데이트, {not_found}건 미발견{excluded_msg}",
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
            raise NotFoundError(f"법령을 찾을 수 없습니다 (ID: {law_id})")

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

        # no_parent_law 플래그 자동 해제 (FR-006a)
        ordinance = await self.get_by_id(ordinance_id)
        if ordinance.no_parent_law:
            ordinance.no_parent_law = False

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
        from sqlalchemy.orm import selectinload

        result = await self.db.execute(
            select(OrdinanceLawMapping)
            .options(selectinload(OrdinanceLawMapping.law))
            .where(OrdinanceLawMapping.id == mapping_id)
        )
        mapping = result.scalar_one_or_none()
        if not mapping:
            raise NotFoundError(f"매핑을 찾을 수 없습니다 (ID: {mapping_id})")

        # 기존 매핑된 Law 레코드를 직접 수정 (새 레코드 생성 방지)
        if law_name is not None or law_type is not None:
            from backend.utils.text import normalize_name
            law = mapping.law
            if law:
                if law_name is not None:
                    law.law_name = normalize_name(law_name)
                if law_type is not None:
                    law.law_type = law_type
                if proclaimed_date:
                    try:
                        law.proclaimed_date = datetime.strptime(proclaimed_date, '%Y-%m-%d').date()
                    except ValueError:
                        pass
                if enforced_date:
                    try:
                        law.enforced_date = datetime.strptime(enforced_date, '%Y-%m-%d').date()
                    except ValueError:
                        pass
            else:
                # 매핑에 법령이 없는 경우에만 새로 찾거나 생성
                law = await self._find_or_create_law(
                    law_name=law_name or "",
                    law_type=law_type or "법률",
                    proclaimed_date=proclaimed_date,
                    enforced_date=enforced_date,
                )
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
            raise NotFoundError(f"매핑을 찾을 수 없습니다 (ID: {mapping_id})")

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
        from backend.utils.text import normalize_name
        name = normalize_name(name)

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
        from backend.utils.text import normalize_name
        name = normalize_name(name)

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
                    print(f"조례 '{ordinance.name}' 업데이트 실패: {e}")
                    failed += 1

        await self.db.commit()

        return {
            "total_ordinances": total_ordinances,
            "updated": updated,
            "failed": failed,
        }

    # ========== revision_status 전환 ==========

    async def start_review(self, ordinance_id: int, user: "User") -> Ordinance:
        """
        검토 시작: revision_status "검토대기"→"검토중" 전환
        - FR-010: 명시적 버튼 클릭으로만 전환
        - FR-017: 부서 담당자 본인 소관 조례만 접근 가능
        """
        from backend.models.user import User

        ordinance = await self.get_by_id(ordinance_id)

        # 부서 담당자 권한 체크: 본인 부서 소관 조례만
        if user.user_type == "DEPARTMENT":
            if not user.department_id or user.department_id != ordinance.department_id:
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=403,
                    detail="본인 부서 소관 조례만 검토할 수 있습니다.",
                )

        # 상태 전환 유효성 검증
        if ordinance.revision_status != "검토대기":
            from fastapi import HTTPException
            raise HTTPException(
                status_code=400,
                detail=f"'검토대기' 상태에서만 검토를 시작할 수 있습니다. (현재: {ordinance.revision_status or 'null'})",
            )

        ordinance.revision_status = "검토중"
        await self.db.commit()
        await self.db.refresh(ordinance)
        return ordinance

    async def clear_revision_status(self, ordinance_id: int) -> Ordinance:
        """
        관리자가 개정확정 상태를 수동 해제 (FR-015)
        revision_status "개정확정"→null
        """
        ordinance = await self.get_by_id(ordinance_id)

        if ordinance.revision_status != "개정확정":
            from fastapi import HTTPException
            raise HTTPException(
                status_code=400,
                detail=f"'개정확정' 상태에서만 해제할 수 있습니다. (현재: {ordinance.revision_status or 'null'})",
            )

        ordinance.revision_status = None
        await self.db.commit()
        await self.db.refresh(ordinance)
        return ordinance

    # ========== 검토이력 CRUD ==========

    async def get_reviews(self, ordinance_id: int) -> List[OrdinanceReview]:
        """조례의 검토이력 목록 조회"""
        await self.get_by_id(ordinance_id)  # 조례 존재 확인

        stmt = (
            select(OrdinanceReview)
            .options(
                selectinload(OrdinanceReview.created_by),
                selectinload(OrdinanceReview.updated_by),
                selectinload(OrdinanceReview.approved_by),
            )
            .where(OrdinanceReview.ordinance_id == ordinance_id)
            .order_by(OrdinanceReview.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_review(
        self,
        ordinance_id: int,
        data: OrdinanceReviewCreate,
        user_id: int,
    ) -> OrdinanceReview:
        """조례 검토이력 추가"""
        await self.get_by_id(ordinance_id)  # 조례 존재 확인

        review = OrdinanceReview(
            ordinance_id=ordinance_id,
            reviewer_type=data.reviewer_type,
            reviewer_name=data.reviewer_name,
            reviewer_department=data.reviewer_department,
            review_content=data.review_content,
            review_result=data.review_result,
            created_by_id=user_id,
            # AI 메타데이터 (006-llm-review-assistant)
            is_ai_generated=getattr(data, 'is_ai_generated', False),
            ai_modified=getattr(data, 'ai_modified', False),
            ai_analysis_id=getattr(data, 'ai_analysis_id', None),
        )

        self.db.add(review)
        await self.db.commit()

        # 관계 로딩을 위해 다시 조회
        result = await self.db.execute(
            select(OrdinanceReview)
            .where(OrdinanceReview.id == review.id)
            .options(
                selectinload(OrdinanceReview.created_by),
                selectinload(OrdinanceReview.updated_by),
                selectinload(OrdinanceReview.approved_by),
            )
        )
        return result.scalar_one()

    async def update_review(
        self,
        review_id: int,
        data: OrdinanceReviewUpdate,
        user_id: int,
    ) -> OrdinanceReview:
        """조례 검토이력 수정"""
        result = await self.db.execute(
            select(OrdinanceReview).where(OrdinanceReview.id == review_id)
        )
        review = result.scalar_one_or_none()
        if not review:
            raise NotFoundError(f"검토이력을 찾을 수 없습니다 (ID: {review_id})")

        if data.reviewer_name is not None:
            review.reviewer_name = data.reviewer_name
        if data.reviewer_department is not None:
            review.reviewer_department = data.reviewer_department
        if data.review_content is not None:
            review.review_content = data.review_content
        if data.review_result is not None:
            review.review_result = data.review_result

        # Set updated_by_id
        review.updated_by_id = user_id

        await self.db.commit()

        # 관계 로딩을 위해 다시 조회
        result = await self.db.execute(
            select(OrdinanceReview)
            .where(OrdinanceReview.id == review_id)
            .options(
                selectinload(OrdinanceReview.created_by),
                selectinload(OrdinanceReview.updated_by),
                selectinload(OrdinanceReview.approved_by),
            )
        )
        return result.scalar_one()

    async def approve_review(
        self,
        review_id: int,
        approval_status: str,
        user_id: int,
        approval_note: Optional[str] = None,
    ) -> OrdinanceReview:
        """
        검토의견 승인/반려 (관리자 전용)
        승인 후 조례 revision_status 자동 처리:
        - 개정필요 + 승인 → "개정확정" (FR-012)
        - 개정불필요 + 승인 → null (FR-013)
        - 반려 → "검토대기" (FR-014)
        """
        result = await self.db.execute(
            select(OrdinanceReview).where(OrdinanceReview.id == review_id)
        )
        review = result.scalar_one_or_none()
        if not review:
            raise NotFoundError(f"검토이력을 찾을 수 없습니다 (ID: {review_id})")

        review.approval_status = approval_status
        review.approved_by_id = user_id
        review.approved_at = datetime.utcnow()
        review.approval_note = approval_note

        # 조례 revision_status 자동 처리
        ordinance = await self.db.get(Ordinance, review.ordinance_id)
        if ordinance:
            if approval_status == "approved":
                if review.review_result == "개정필요":
                    ordinance.revision_status = "개정확정"
                elif review.review_result == "개정불필요":
                    ordinance.revision_status = "검토완료"  # null 대신 검토완료 (재플래그 방지)

                # 매핑별 reviewed_law_date 기록 (동일 법령 변경 재감지 방지)
                mappings_result = await self.db.execute(
                    select(OrdinanceLawMapping)
                    .options(selectinload(OrdinanceLawMapping.law))
                    .where(OrdinanceLawMapping.ordinance_id == review.ordinance_id)
                )
                for mapping in mappings_result.scalars().all():
                    if mapping.law and mapping.law.proclaimed_date:
                        mapping.reviewed_law_date = mapping.law.proclaimed_date

            elif approval_status == "rejected":
                ordinance.revision_status = "재검토중"  # 반려 → 재검토중 (빨간색 표시, 담당자가 바로 새 검토의견 등록 가능)

        await self.db.commit()

        # Reload with relationships
        result = await self.db.execute(
            select(OrdinanceReview)
            .where(OrdinanceReview.id == review_id)
            .options(
                selectinload(OrdinanceReview.created_by),
                selectinload(OrdinanceReview.updated_by),
                selectinload(OrdinanceReview.approved_by),
            )
        )
        return result.scalar_one()

    async def delete_review(self, review_id: int) -> bool:
        """조례 검토이력 삭제"""
        result = await self.db.execute(
            select(OrdinanceReview).where(OrdinanceReview.id == review_id)
        )
        review = result.scalar_one_or_none()
        if not review:
            raise NotFoundError(f"검토이력을 찾을 수 없습니다 (ID: {review_id})")

        await self.db.delete(review)
        await self.db.commit()
        return True
