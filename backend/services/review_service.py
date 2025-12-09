"""
Review Service
"""
from typing import Optional
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.review import AmendmentReview
from backend.schemas.review import ReviewUpdate
from backend.core.exceptions import NotFoundError


class ReviewService:
    """Review management service"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_list(
        self,
        page: int = 1,
        size: int = 20,
        need_revision: Optional[bool] = None,
        status: Optional[str] = None,
        urgency: Optional[str] = None,
    ) -> dict:
        """Get paginated list of reviews"""
        query = select(AmendmentReview)

        if need_revision is not None:
            query = query.where(AmendmentReview.need_revision == need_revision)
        if status:
            query = query.where(AmendmentReview.status == status)
        if urgency:
            query = query.where(AmendmentReview.revision_urgency == urgency)

        query = query.order_by(AmendmentReview.created_at.desc())

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

    async def get_by_id(self, review_id: int) -> AmendmentReview:
        """Get review by ID"""
        result = await self.db.execute(
            select(AmendmentReview).where(AmendmentReview.id == review_id)
        )
        review = result.scalar_one_or_none()
        if not review:
            raise NotFoundError(f"Review {review_id} not found")
        return review

    async def update(self, review_id: int, update_data: ReviewUpdate) -> AmendmentReview:
        """Update review"""
        review = await self.get_by_id(review_id)

        if update_data.status:
            review.status = update_data.status
        if update_data.reviewed_by:
            review.reviewed_by = update_data.reviewed_by
            review.reviewed_at = datetime.utcnow()
        if update_data.reason:
            review.reason = update_data.reason
        if update_data.recommendation:
            review.recommendation = update_data.recommendation

        await self.db.commit()
        await self.db.refresh(review)
        return review

    async def generate_report(self) -> dict:
        """Generate revision report"""
        # Get reviews needing revision
        result = await self.db.execute(
            select(AmendmentReview).where(
                AmendmentReview.need_revision == True,
                AmendmentReview.status == "PENDING",
            )
        )
        reviews = result.scalars().all()

        by_urgency = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        items = []

        for review in reviews:
            if review.revision_urgency:
                by_urgency[review.revision_urgency] = by_urgency.get(review.revision_urgency, 0) + 1

            # TODO: Join with ordinance and amendment for full info
            items.append({
                "ordinance_name": f"Ordinance #{review.ordinance_id}",
                "department": None,
                "law_name": f"Law #{review.amendment_id}",
                "urgency": review.revision_urgency or "LOW",
                "affected_count": len(review.affected_articles or []),
                "reason": review.reason,
            })

        return {
            "generated_at": datetime.utcnow(),
            "total_need_revision": len(reviews),
            "by_urgency": by_urgency,
            "items": items,
        }
