"""
Dashboard API endpoints
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db
from backend.schemas.dashboard import (
    DashboardSummary,
    RecentAmendments,
    PendingReviews,
)
from backend.services.dashboard_service import DashboardService

router = APIRouter()


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_db),
):
    """Get dashboard summary"""
    service = DashboardService(db)
    return await service.get_summary()


@router.get("/recent-amendments", response_model=RecentAmendments)
async def get_recent_amendments(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """Get recent law amendments"""
    service = DashboardService(db)
    return await service.get_recent_amendments(limit)


@router.get("/pending-reviews", response_model=PendingReviews)
async def get_pending_reviews(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """Get pending reviews"""
    service = DashboardService(db)
    return await service.get_pending_reviews(limit)
