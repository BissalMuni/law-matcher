"""
Amendment Service
"""
from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.amendment import LawAmendment
from backend.core.exceptions import NotFoundError


class AmendmentService:
    """Amendment detection and management"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_list(
        self,
        page: int = 1,
        size: int = 20,
        law_id: Optional[str] = None,
        processed: Optional[bool] = None,
    ) -> dict:
        """Get paginated list of amendments"""
        query = select(LawAmendment)

        if law_id:
            query = query.where(LawAmendment.law_id == law_id)
        if processed is not None:
            query = query.where(LawAmendment.processed == processed)

        query = query.order_by(LawAmendment.detected_at.desc())

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

    async def get_by_id(self, amendment_id: int) -> LawAmendment:
        """Get amendment by ID"""
        result = await self.db.execute(
            select(LawAmendment).where(LawAmendment.id == amendment_id)
        )
        amendment = result.scalar_one_or_none()
        if not amendment:
            raise NotFoundError(f"Amendment {amendment_id} not found")
        return amendment

    async def analyze_impact(self, amendment_id: int) -> dict:
        """Run impact analysis for amendment"""
        amendment = await self.get_by_id(amendment_id)

        # TODO: Implement actual analysis logic
        # 1. Get ordinances linked to this law
        # 2. Compare article content
        # 3. Create review records

        return {
            "amendment_id": amendment_id,
            "affected_ordinances": 0,
            "need_revision_count": 0,
            "reviews_created": 0,
        }
