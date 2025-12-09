"""
Laws API endpoints - 상위법령 관리
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.api.deps import get_db
from backend.models.law import Law
from backend.models.ordinance_law_mapping import OrdinanceLawMapping
from backend.schemas.ordinance import (
    LawResponse,
    LawBriefResponse,
    OrdinanceLawMappingResponse,
    OrdinanceLawMappingCreate,
    OrdinanceLawMappingUpdate,
    LawSyncRequest,
    LawSyncResponse,
    AmendmentCheckRequest,
    AmendmentCheckResponse,
)
from backend.services.law_sync_service import LawSyncService

router = APIRouter()


@router.get("", response_model=List[LawResponse])
async def get_laws(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    law_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """상위법령 목록 조회"""
    query = select(Law)

    if search:
        query = query.where(Law.law_name.ilike(f"%{search}%"))
    if law_type:
        query = query.where(Law.law_type == law_type)

    query = query.order_by(Law.law_name).offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/count")
async def get_laws_count(
    search: Optional[str] = None,
    law_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """상위법령 개수 조회"""
    query = select(func.count(Law.id))

    if search:
        query = query.where(Law.law_name.ilike(f"%{search}%"))
    if law_type:
        query = query.where(Law.law_type == law_type)

    result = await db.scalar(query)
    return {"count": result}


@router.get("/types")
async def get_law_types(
    db: AsyncSession = Depends(get_db),
):
    """법령 유형 목록 조회"""
    result = await db.execute(
        select(Law.law_type, func.count(Law.id).label("count"))
        .group_by(Law.law_type)
        .order_by(Law.law_type)
    )
    rows = result.all()
    return [{"type": row[0], "count": row[1]} for row in rows]


@router.get("/{law_id}", response_model=LawResponse)
async def get_law(
    law_id: int,
    db: AsyncSession = Depends(get_db),
):
    """상위법령 상세 조회"""
    result = await db.execute(select(Law).where(Law.id == law_id))
    law = result.scalar_one_or_none()
    if not law:
        raise HTTPException(status_code=404, detail="Law not found")
    return law


@router.get("/{law_id}/ordinances")
async def get_law_ordinances(
    law_id: int,
    db: AsyncSession = Depends(get_db),
):
    """특정 법령과 연계된 조례 목록"""
    result = await db.execute(
        select(OrdinanceLawMapping)
        .options(selectinload(OrdinanceLawMapping.ordinance))
        .where(OrdinanceLawMapping.law_id == law_id)
    )
    mappings = result.scalars().all()

    return [
        {
            "mapping_id": m.id,
            "ordinance_id": m.ordinance.id,
            "ordinance_name": m.ordinance.name,
            "ordinance_category": m.ordinance.category,
            "related_articles": m.related_articles,
        }
        for m in mappings
    ]


@router.post("/sync", response_model=LawSyncResponse)
async def sync_laws(
    request: LawSyncRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    법령 동기화

    - lnkOrg API에서 조례-법령 연계 정보를 가져옴
    - 연계된 법령들을 law API로 조회하여 laws 테이블에 저장
    - ordinance_law_mappings 테이블에 연계 정보 저장
    """
    service = LawSyncService(db)

    try:
        result = await service.sync_from_lnk_org(sborg=request.sborg)

        return LawSyncResponse(
            success=True,
            synced_laws=result["synced_laws"],
            synced_mappings=result["synced_mappings"],
            message=f"동기화 완료: 법령 {result['synced_laws']}건, 매핑 {result['synced_mappings']}건",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check-amendments", response_model=List[AmendmentCheckResponse])
async def check_amendments(
    request: AmendmentCheckRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    개정 감지

    최근 N일간 공포된 법령 중 개정된 법령을 찾아
    해당 법령과 연계된 조례를 개정 대상으로 식별
    """
    service = LawSyncService(db)

    try:
        results = await service.check_amendments(days=request.days)

        response = []
        for r in results:
            law = r["law"]
            ordinances = r["affected_ordinances"]

            response.append(AmendmentCheckResponse(
                law_name=law.law_name,
                old_proclaimed_date=r["old_proclaimed_date"],
                new_proclaimed_date=r["new_proclaimed_date"],
                revision_type=r["revision_type"],
                affected_ordinance_count=len(ordinances),
                affected_ordinances=[o.name for o in ordinances],
            ))

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check-amendments/create-targets")
async def create_amendment_targets(
    request: AmendmentCheckRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    개정 감지 후 개정 대상 레코드 생성

    check_amendments로 감지된 결과를 바탕으로
    LawAmendment 레코드를 생성
    """
    service = LawSyncService(db)

    try:
        # 개정 감지
        results = await service.check_amendments(days=request.days)

        # 개정 대상 레코드 생성
        amendments = await service.create_amendment_targets(results)

        return {
            "success": True,
            "created_amendments": len(amendments),
            "message": f"개정 대상 {len(amendments)}건 생성 완료",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
