"""
Dashboard Service
"""
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.ordinance import Ordinance
from backend.models.law import Law
from backend.models.amendment import LawAmendment
from backend.models.review import AmendmentReview


class DashboardService:
    """Dashboard data service"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_summary(self) -> dict:
        """Get dashboard summary"""
        # Total ordinances
        total_ordinances = await self.db.scalar(
            select(func.count()).select_from(Ordinance).where(Ordinance.status == "ACTIVE")
        )

        # Total parent laws (from laws table)
        total_parent_laws = await self.db.scalar(
            select(func.count()).select_from(Law)
        )

        # Recent amendments (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_amendments = await self.db.scalar(
            select(func.count()).select_from(LawAmendment).where(
                LawAmendment.detected_at >= thirty_days_ago
            )
        )

        # Pending reviews
        pending_reviews = await self.db.scalar(
            select(func.count()).select_from(AmendmentReview).where(
                AmendmentReview.status == "PENDING"
            )
        )

        # Need revision count
        need_revision_count = await self.db.scalar(
            select(func.count()).select_from(AmendmentReview).where(
                AmendmentReview.need_revision == True,
                AmendmentReview.status == "PENDING",
            )
        )

        return {
            "total_ordinances": total_ordinances or 0,
            "total_parent_laws": total_parent_laws or 0,
            "recent_amendments": recent_amendments or 0,
            "pending_reviews": pending_reviews or 0,
            "need_revision_count": need_revision_count or 0,
            "last_sync_at": None,  # TODO: Track last sync time
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
            # Count affected ordinances
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
                "ordinance_name": f"Ordinance #{review.ordinance_id}",  # TODO: Join
                "law_name": f"Law #{review.amendment_id}",  # TODO: Join
                "urgency": review.revision_urgency or "LOW",
                "created_at": review.created_at,
            })

        return {"items": items}
