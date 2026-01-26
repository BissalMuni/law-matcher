"""
Laws API endpoints - 상위법령 관리
"""
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
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
    LawSearchRequest,
    LawSearchResponse,
    LawInfoUpdateResponse,
)
from backend.services.law_sync_service import LawSyncService

router = APIRouter()


@router.get("", response_model=List[LawResponse])
async def get_laws(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    law_type: Optional[str] = None,
    dept_name: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """상위법령 목록 조회 (담당부서는 연계 자치법규 기준 필터링)"""
    from backend.models.ordinance import Ordinance

    if dept_name:
        # 담당부서 필터: 연계된 자치법규의 담당부서로 필터링
        subquery = (
            select(OrdinanceLawMapping.law_id)
            .join(Ordinance, OrdinanceLawMapping.ordinance_id == Ordinance.id)
            .where(Ordinance.department == dept_name)
            .distinct()
        )
        query = select(Law).where(Law.id.in_(subquery))
    else:
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
    dept_name: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """상위법령 개수 조회 (담당부서는 연계 자치법규 기준 필터링)"""
    from backend.models.ordinance import Ordinance

    if dept_name:
        # 담당부서 필터: 연계된 자치법규의 담당부서로 필터링
        subquery = (
            select(OrdinanceLawMapping.law_id)
            .join(Ordinance, OrdinanceLawMapping.ordinance_id == Ordinance.id)
            .where(Ordinance.department == dept_name)
            .distinct()
        )
        query = select(func.count(Law.id)).where(Law.id.in_(subquery))
    else:
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


@router.get("/departments")
async def get_law_departments(
    db: AsyncSession = Depends(get_db),
):
    """상위법령 담당부서 목록 조회 (연계된 자치법규의 담당부서 기준)"""
    from backend.models.ordinance import Ordinance

    # 연계된 자치법규의 담당부서별 법령 개수 조회
    result = await db.execute(
        select(Ordinance.department, func.count(func.distinct(Law.id)).label("count"))
        .select_from(Law)
        .join(OrdinanceLawMapping, Law.id == OrdinanceLawMapping.law_id)
        .join(Ordinance, OrdinanceLawMapping.ordinance_id == Ordinance.id)
        .where(Ordinance.department.isnot(None))
        .where(Ordinance.department != '')
        .group_by(Ordinance.department)
        .order_by(Ordinance.department)
    )
    rows = result.all()
    return [{"name": row[0], "count": row[1]} for row in rows]


@router.get("/sync-stream")
async def sync_laws_stream():
    """
    법령 동기화 (SSE 스트리밍)

    모든 상위법령을 법제처 API와 비교하여 변경사항을 실시간으로 스트리밍합니다.
    - 진행 상황 (요청/수신/비교)
    - 변경된 법령 정보
    - 최종 결과
    """
    from backend.core.database import async_session

    async def event_generator():
        async with async_session() as db:
            try:
                service = LawSyncService(db)
                async for event in service.sync_all_laws_with_progress():
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            except Exception as e:
                error_event = {
                    "type": "error",
                    "message": f"동기화 중 오류 발생: {str(e)}",
                    "error": str(e),
                }
                yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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


@router.post("/search", response_model=LawSearchResponse)
async def search_law_by_name(
    request: LawSearchRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    법령명으로 법제처 API에서 검색하여 법령ID 반환
    - 정확히 일치하는 법령명만 성공
    - 검색 결과가 없거나 정확히 일치하지 않으면 실패
    """
    import httpx
    from backend.core.config import settings
    
    api_key = settings.MOLEG_API_KEY or "test"
    url = "http://www.law.go.kr/DRF/lawSearch.do"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                url,
                params={
                    "OC": api_key,
                    "target": "law",
                    "type": "JSON",
                    "query": request.law_name,
                },
            )
            response.raise_for_status()
            data = response.json()
            
            laws = data.get("LawSearch", {}).get("law", [])
            
            if not laws:
                return LawSearchResponse(
                    success=False,
                    message=f"'{request.law_name}' 법령을 찾을 수 없습니다.",
                )
            
            # 정확히 일치하는 법령명 찾기
            exact_match = None
            for law in laws:
                if law.get("법령명한글") == request.law_name:
                    exact_match = law
                    break
            
            if not exact_match:
                return LawSearchResponse(
                    success=False,
                    message=f"'{request.law_name}'와 정확히 일치하는 법령명이 없습니다. 입력한 법령명을 확인해주세요.",
                )
            
            return LawSearchResponse(
                success=True,
                law_id=exact_match.get("법령ID"),
                law_serial_no=exact_match.get("법령일련번호"),
                law_name=exact_match.get("법령명한글"),
                law_type=exact_match.get("법령구분명"),
                message="법령 검색 성공",
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"법령 검색 중 오류 발생: {str(e)}",
        )


@router.post("/update-all-info", response_model=LawInfoUpdateResponse)
async def update_all_law_info(
    db: AsyncSession = Depends(get_db),
):
    """
    모든 상위법령의 정보를 법제처 API로 업데이트

    - laws 테이블의 모든 법령명에 대해 법제처 API 호출
    - 공포일, 시행일, 법령ID 등 정보 업데이트
    """
    service = LawSyncService(db)

    try:
        result = await service.update_all_law_info()
        return LawInfoUpdateResponse(
            success=True,
            total_laws=result["total_laws"],
            updated=result["updated"],
            failed=result["failed"],
            message=f"법령 정보 업데이트 완료: {result['updated']}건 성공, {result['failed']}건 실패",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"법령 정보 업데이트 중 오류 발생: {str(e)}",
        )


@router.delete("/{law_id}")
async def delete_law(
    law_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    법령 삭제 (laws + law_changes + ordinance_law_mappings 모두 삭제)
    """
    from backend.models.law_change import LawChange

    # 법령 존재 확인
    law = await db.get(Law, law_id)
    if not law:
        raise HTTPException(status_code=404, detail="법령을 찾을 수 없습니다.")

    law_name = law.law_name

    # 1. law_changes 삭제
    await db.execute(
        select(LawChange).where(LawChange.law_id == law_id)
    )
    law_changes_result = await db.execute(
        select(LawChange).where(LawChange.law_id == law_id)
    )
    for lc in law_changes_result.scalars().all():
        await db.delete(lc)

    # 2. ordinance_law_mappings 삭제
    mappings_result = await db.execute(
        select(OrdinanceLawMapping).where(OrdinanceLawMapping.law_id == law_id)
    )
    for mapping in mappings_result.scalars().all():
        await db.delete(mapping)

    # 3. law 삭제
    await db.delete(law)
    await db.commit()

    return {
        "success": True,
        "message": f"법령 '{law_name}' 및 관련 데이터가 삭제되었습니다.",
    }
