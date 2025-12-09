"""
Review API endpoints
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db
from backend.schemas.review import (
    ReviewResponse,
    ReviewListResponse,
    ReviewUpdate,
    ReviewReportResponse,
)
from backend.services.review_service import ReviewService

router = APIRouter()


@router.get("", response_model=ReviewListResponse)
async def get_reviews(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    need_revision: Optional[bool] = None,
    status: Optional[str] = None,
    urgency: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get list of amendment reviews"""
    service = ReviewService(db)
    return await service.get_list(
        page=page,
        size=size,
        need_revision=need_revision,
        status=status,
        urgency=urgency,
    )


@router.get("/report", response_model=ReviewReportResponse)
async def get_review_report(
    db: AsyncSession = Depends(get_db),
):
    """Generate revision report"""
    service = ReviewService(db)
    return await service.generate_report()


@router.get("/{review_id}", response_model=ReviewResponse)
async def get_review(
    review_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get review details"""
    service = ReviewService(db)
    return await service.get_by_id(review_id)


@router.patch("/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: int,
    update_data: ReviewUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update review status"""
    service = ReviewService(db)
    return await service.update(review_id, update_data)
