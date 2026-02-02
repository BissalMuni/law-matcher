"""
Dashboard Service
"""
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy import select, func, case, Integer, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.ordinance import Ordinance
from backend.models.law import Law
from backend.models.amendment import LawAmendment
from backend.models.review import AmendmentReview
from backend.models.ordinance_law_mapping import OrdinanceLawMapping
from backend.models.law_change import LawChange, ApiStatus


class DashboardService:
    """Dashboard data service"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_summary(self) -> dict:
        """Get dashboard summary"""
        total_ordinances = await self.db.scalar(
            select(func.count()).select_from(Ordinance).where(Ordinance.status == "ACTIVE")
        )

        total_parent_laws = await self.db.scalar(
            select(func.count()).select_from(Law)
        )

        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_amendments = await self.db.scalar(
            select(func.count()).select_from(LawAmendment).where(
                LawAmendment.detected_at >= thirty_days_ago
            )
        )

        pending_reviews = await self.db.scalar(
            select(func.count()).select_from(AmendmentReview).where(
                AmendmentReview.status == "PENDING"
            )
        )

        need_revision_count = await self.db.scalar(
            select(func.count()).select_from(AmendmentReview).where(
                AmendmentReview.need_revision == True,
                AmendmentReview.status == "PENDING",
            )
        )

        revision_needs_action_count = await self.db.scalar(
            select(func.count(func.distinct(Ordinance.id)))
            .select_from(Ordinance)
            .join(OrdinanceLawMapping, Ordinance.id == OrdinanceLawMapping.ordinance_id)
            .join(Law, OrdinanceLawMapping.law_id == Law.id)
            .where(
                Ordinance.revision_date.isnot(None),
                Law.proclaimed_date.isnot(None),
                Ordinance.revision_date < Law.proclaimed_date
            )
        )

        revision_completed_count = await self.db.scalar(
            select(func.count(func.distinct(Ordinance.id)))
            .select_from(Ordinance)
            .join(OrdinanceLawMapping, Ordinance.id == OrdinanceLawMapping.ordinance_id)
            .join(Law, OrdinanceLawMapping.law_id == Law.id)
            .where(
                Ordinance.revision_date.isnot(None),
                Law.proclaimed_date.isnot(None),
                Ordinance.revision_date >= Law.proclaimed_date
            )
        )

        return {
            "total_ordinances": total_ordinances or 0,
            "total_parent_laws": total_parent_laws or 0,
            "recent_amendments": recent_amendments or 0,
            "pending_reviews": pending_reviews or 0,
            "need_revision_count": need_revision_count or 0,
            "revision_needs_action_count": revision_needs_action_count or 0,
            "revision_completed_count": revision_completed_count or 0,
            "last_sync_at": None,
        }

    async def get_recent_amendments(self, limit: int = 10) -> dict:
        """Get recent amendments"""
        result = await self.db.execute(
            select(LawAmendment)
            .order_by(LawAmendment.detected_at.desc())
            .limit(limit)
        )
        amendments = result.scalars().all()

        items = []
        for amendment in amendments:
            affected_count = await self.db.scalar(
                select(func.count()).select_from(AmendmentReview).where(
                    AmendmentReview.amendment_id == amendment.id
                )
            )
            items.append({
                "id": amendment.id,
                "law_name": amendment.law_name,
                "change_type": amendment.change_type,
                "detected_at": amendment.detected_at,
                "affected_ordinances": affected_count or 0,
            })

        return {"items": items}

    async def get_pending_reviews(self, limit: int = 10) -> dict:
        """Get pending reviews"""
        result = await self.db.execute(
            select(AmendmentReview)
            .where(
                AmendmentReview.need_revision == True,
                AmendmentReview.status == "PENDING",
            )
            .order_by(AmendmentReview.created_at.desc())
            .limit(limit)
        )
        reviews = result.scalars().all()

        items = []
        for review in reviews:
            items.append({
                "id": review.id,
                "ordinance_name": f"Ordinance #{review.ordinance_id}",
                "law_name": f"Law #{review.amendment_id}",
                "urgency": review.revision_urgency or "LOW",
                "created_at": review.created_at,
            })

        return {"items": items}

    async def get_latest_sync_stats(self) -> dict:
        """최근 동기화 통계 - 개정구분별 건수"""
        # 가장 최근 sync_date 조회
        latest_sync_date = await self.db.scalar(
            select(func.max(LawChange.sync_date))
        )
        if not latest_sync_date:
            return {"sync_date": None, "total_laws": 0, "by_revision_type": []}

        # 해당 sync_date의 법령 변경 건수 (날짜 기준으로 필터)
        date_filter = func.date(LawChange.sync_date) == latest_sync_date.date()

        total_laws = await self.db.scalar(
            select(func.count(LawChange.id))
            .where(date_filter, LawChange.api_status == ApiStatus.SUCCESS)
        )

        # 개정구분별 건수 (Law.revision_type 기준)
        revision_type_query = (
            select(
                Law.revision_type,
                func.count(LawChange.id).label("count"),
            )
            .select_from(LawChange)
            .join(Law, LawChange.law_id == Law.id)
            .where(date_filter, LawChange.api_status == ApiStatus.SUCCESS)
            .group_by(Law.revision_type)
            .order_by(func.count(LawChange.id).desc())
        )
        result = await self.db.execute(revision_type_query)
        by_revision_type = [
            {"revision_type": row[0] or "미분류", "count": row[1]}
            for row in result.all()
        ]

        return {
            "sync_date": latest_sync_date,
            "total_laws": total_laws or 0,
            "by_revision_type": by_revision_type,
        }

    async def get_revision_needed(
        self,
        limit: int = 10,
        status: Optional[str] = None,
        department: Optional[str] = None
    ) -> dict:
        """Get revision-needed items."""
        revision_status_case = case(
            (Ordinance.revision_date < Law.proclaimed_date, "NEEDS_REVISION"),
            else_="COMPLETED"
        ).label("revision_status")

        days_diff_case = (
            Law.proclaimed_date - Ordinance.revision_date
        ).cast(Integer).label("days_diff")

        query = (
            select(
                Ordinance.id.label("ordinance_id"),
                Ordinance.name.label("ordinance_name"),
                Ordinance.revision_date.label("ordinance_revision_date"),
                Ordinance.department,
                Law.id.label("law_id"),
                Law.law_name,
                Law.law_type,
                Law.proclaimed_date.label("law_proclaimed_date"),
                days_diff_case,
                revision_status_case,
            )
            .select_from(Ordinance)
            .join(OrdinanceLawMapping, Ordinance.id == OrdinanceLawMapping.ordinance_id)
            .join(Law, OrdinanceLawMapping.law_id == Law.id)
            .where(
                Ordinance.revision_date.isnot(None),
                Law.proclaimed_date.isnot(None)
            )
        )

        if status:
            if status == "NEEDS_REVISION":
                query = query.where(Ordinance.revision_date < Law.proclaimed_date)
            elif status == "COMPLETED":
                query = query.where(Ordinance.revision_date >= Law.proclaimed_date)

        if department:
            query = query.where(Ordinance.department == department)

        query = query.order_by(
            case(
                (Ordinance.revision_date < Law.proclaimed_date, 1),
                else_=2
            ),
            func.abs(days_diff_case).desc()
        ).limit(limit)

        result = await self.db.execute(query)
        rows = result.all()

        items = []
        for row in rows:
            items.append({
                "ordinance_id": row.ordinance_id,
                "ordinance_name": row.ordinance_name,
                "ordinance_revision_date": row.ordinance_revision_date,
                "law_id": row.law_id,
                "law_name": row.law_name,
                "law_type": row.law_type,
                "law_proclaimed_date": row.law_proclaimed_date,
                "days_diff": row.days_diff,
                "revision_status": row.revision_status,
                "department": row.department,
            })

        needs_revision_count = await self.db.scalar(
            select(func.count(func.distinct(Ordinance.id)))
            .select_from(Ordinance)
            .join(OrdinanceLawMapping, Ordinance.id == OrdinanceLawMapping.ordinance_id)
            .join(Law, OrdinanceLawMapping.law_id == Law.id)
            .where(
                Ordinance.revision_date.isnot(None),
                Law.proclaimed_date.isnot(None),
                Ordinance.revision_date < Law.proclaimed_date
            )
        )

        completed_count = await self.db.scalar(
            select(func.count(func.distinct(Ordinance.id)))
            .select_from(Ordinance)
            .join(OrdinanceLawMapping, Ordinance.id == OrdinanceLawMapping.ordinance_id)
            .join(Law, OrdinanceLawMapping.law_id == Law.id)
            .where(
                Ordinance.revision_date.isnot(None),
                Law.proclaimed_date.isnot(None),
                Ordinance.revision_date >= Law.proclaimed_date
            )
        )

        return {
            "total": len(items),
            "needs_revision_count": needs_revision_count or 0,
            "completed_count": completed_count or 0,
            "items": items,
        }

    async def get_ordinance_revision_tree(self) -> dict:
        """자치법규 개정 현황 트리 - 전체법령/개정대상아님/개정대상(제개정구분별)"""
        # 조례별 상위법령 최대 시행일 vs 조례 공포일 비교 (ordinance_service와 동일 로직)
        base_join = (
            select(
                Ordinance.id.label("ordinance_id"),
                func.max(Law.enforced_date).label("max_enforced_date"),
                Ordinance.enacted_date,
            )
            .select_from(Ordinance)
            .join(OrdinanceLawMapping, Ordinance.id == OrdinanceLawMapping.ordinance_id)
            .join(Law, OrdinanceLawMapping.law_id == Law.id)
            .where(
                Ordinance.status == "ACTIVE",
                Ordinance.enacted_date.isnot(None),
                Law.enforced_date.isnot(None),
            )
            .group_by(Ordinance.id, Ordinance.enacted_date)
        ).subquery()

        # 전체 (상위법령 매핑이 있는 자치법규)
        total_count = await self.db.scalar(
            select(func.count()).select_from(base_join)
        )

        # 개정대상 (max_enforced_date > enacted_date)
        needs_revision_count = await self.db.scalar(
            select(func.count()).select_from(base_join).where(
                base_join.c.max_enforced_date > base_join.c.enacted_date
            )
        )

        # 개정대상아님
        no_revision_count = await self.db.scalar(
            select(func.count()).select_from(base_join).where(
                base_join.c.max_enforced_date <= base_join.c.enacted_date
            )
        )

        # 개정대상 중 제개정구분별 건수
        needs_revision_ordinances = (
            select(base_join.c.ordinance_id)
            .where(base_join.c.max_enforced_date > base_join.c.enacted_date)
        ).subquery()

        revision_type_query = (
            select(
                Law.revision_type,
                func.count(func.distinct(OrdinanceLawMapping.ordinance_id)).label("count"),
            )
            .select_from(OrdinanceLawMapping)
            .join(Law, OrdinanceLawMapping.law_id == Law.id)
            .where(
                OrdinanceLawMapping.ordinance_id.in_(
                    select(needs_revision_ordinances.c.ordinance_id)
                ),
                Law.enforced_date.isnot(None),
                Law.revision_type.isnot(None),
                Law.revision_type != '',
            )
            .group_by(Law.revision_type)
            .order_by(func.count(func.distinct(OrdinanceLawMapping.ordinance_id)).desc())
        )
        result = await self.db.execute(revision_type_query)
        by_revision_type = [
            {"revision_type": row[0], "count": row[1]}
            for row in result.all()
        ]

        return {
            "total_count": total_count or 0,
            "no_revision_count": no_revision_count or 0,
            "needs_revision_count": needs_revision_count or 0,
            "by_revision_type": by_revision_type,
        }
