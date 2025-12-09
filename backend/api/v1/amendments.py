"""
Amendment API endpoints
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db
from backend.schemas.amendment import AmendmentResponse, AmendmentListResponse
from backend.services.amendment_service import AmendmentService

router = APIRouter()


@router.get("", response_model=AmendmentListResponse)
async def get_amendments(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    law_id: Optional[str] = None,
    processed: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get list of detected amendments"""
    service = AmendmentService(db)
    return await service.get_list(
        page=page,
        size=size,
        law_id=law_id,
        processed=processed,
    )


@router.get("/{amendment_id}", response_model=AmendmentResponse)
async def get_amendment(
    amendment_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get amendment details"""
    service = AmendmentService(db)
    return await service.get_by_id(amendment_id)


@router.post("/{amendment_id}/analyze")
async def analyze_amendment(
    amendment_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Run impact analysis for an amendment"""
    service = AmendmentService(db)
    return await service.analyze_impact(amendment_id)
