"""
Dashboard API endpoints
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db
from backend.schemas.dashboard import (
    DashboardSummary,
    RecentAmendments,
    PendingReviews,
    RevisionNeededListResponse,
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


@router.get("/revision-needed", response_model=RevisionNeededListResponse)
async def get_revision_needed(
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None, regex="^(NEEDS_REVISION|UNDER_REVIEW|COMPLETED)$"),
    department: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get revision-needed items grouped by status."""
    service = DashboardService(db)
    return await service.get_revision_needed(limit, status, department)
