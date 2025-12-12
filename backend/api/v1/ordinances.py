"""
Ordinance API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db, verify_admin_password
from backend.schemas.ordinance import (
    OrdinanceResponse,
    OrdinanceListResponse,
    OrdinanceSyncRequest,
    OrdinanceSyncResponse,
    OrdinanceUploadResponse,
    OrdinanceLawMappingCreate,
    OrdinanceLawMappingUpdate,
    ParentLawCreate,
)
from backend.services.ordinance_service import OrdinanceService
from backend.core.exceptions import NotFoundError

router = APIRouter()


@router.get("", response_model=OrdinanceListResponse)
async def get_ordinances(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    department: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get list of ordinances"""
    service = OrdinanceService(db)
    return await service.get_list(
        page=page,
        size=size,
        category=category,
        department=department,
        search=search,
    )


@router.get("/departments")
async def get_departments(
    db: AsyncSession = Depends(get_db),
):
    """소관부서 목록 조회 (트리용)"""
    service = OrdinanceService(db)
    return await service.get_departments()


@router.post("/sync", response_model=OrdinanceSyncResponse)
async def sync_ordinances(
    request: OrdinanceSyncRequest = OrdinanceSyncRequest(),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_password),
):
    """법제처 API에서 자치법규 목록을 가져와 DB에 저장 (관리자 전용)"""
    service = OrdinanceService(db)
    return await service.sync_from_moleg(org=request.org, sborg=request.sborg)


@router.post("/upload", response_model=OrdinanceUploadResponse)
async def upload_ordinances(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_password),
):
    """엑셀 파일로 소관부서 정보 일괄 업데이트 (관리자 전용)"""
    service = OrdinanceService(db)
    return await service.upload_from_excel(file)


@router.get("/{ordinance_id}", response_model=OrdinanceResponse)
async def get_ordinance(
    ordinance_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get ordinance by ID"""
    service = OrdinanceService(db)
    return await service.get_by_id(ordinance_id)


@router.get("/{ordinance_id}/articles")
async def get_ordinance_articles(
    ordinance_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get ordinance articles"""
    service = OrdinanceService(db)
    return await service.get_articles(ordinance_id)


@router.get("/{ordinance_id}/parent-laws")
async def get_parent_laws(
    ordinance_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    조례에 매핑된 상위법령 목록 조회 (새 구조)

    Returns:
        법령 매핑 정보 목록 (법령 상세 정보 포함)
    """
    service = OrdinanceService(db)
    return await service.get_parent_laws(ordinance_id)


@router.post("/{ordinance_id}/parent-laws")
async def create_parent_law(
    ordinance_id: int,
    data: ParentLawCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    상위법령 추가 (프론트엔드 호환)

    Args:
        ordinance_id: 조례 ID
        data: 상위법령 정보
    """
    service = OrdinanceService(db)
    try:
        result = await service.create_parent_law(
            ordinance_id=ordinance_id,
            law_name=data.law_name,
            law_type=data.law_type,
            proclaimed_date=data.proclaimed_date,
            enforced_date=data.enforced_date,
            related_articles=data.related_articles,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/parent-laws/{parent_law_id}")
async def update_parent_law(
    parent_law_id: int,
    data: OrdinanceLawMappingUpdate,
    db: AsyncSession = Depends(get_db),
):
    """상위법령 매핑 수정 (프론트엔드 호환)"""
    service = OrdinanceService(db)
    try:
        mapping = await service.update_law_mapping(
            mapping_id=parent_law_id,
            related_articles=data.related_articles,
        )
        return {"success": True, "id": mapping.id, "message": "수정되었습니다."}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/parent-laws/{parent_law_id}")
async def delete_parent_law(
    parent_law_id: int,
    db: AsyncSession = Depends(get_db),
):
    """상위법령 매핑 삭제 (프론트엔드 호환)"""
    service = OrdinanceService(db)
    try:
        await service.delete_law_mapping(parent_law_id)
        return {"success": True, "message": "삭제되었습니다."}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{ordinance_id}/law-mappings")
async def create_law_mapping(
    ordinance_id: int,
    data: OrdinanceLawMappingCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    조례-법령 매핑 추가

    Args:
        ordinance_id: 조례 ID
        data: 매핑 정보 (law_id, related_articles)
    """
    service = OrdinanceService(db)
    try:
        mapping = await service.create_law_mapping(
            ordinance_id=ordinance_id,
            law_id=data.law_id,
            related_articles=data.related_articles,
        )
        return {"success": True, "id": mapping.id, "message": "매핑이 추가되었습니다."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/law-mappings/{mapping_id}")
async def update_law_mapping(
    mapping_id: int,
    data: OrdinanceLawMappingUpdate,
    db: AsyncSession = Depends(get_db),
):
    """조례-법령 매핑 수정"""
    service = OrdinanceService(db)
    try:
        mapping = await service.update_law_mapping(
            mapping_id=mapping_id,
            related_articles=data.related_articles,
        )
        return {"success": True, "id": mapping.id, "message": "수정되었습니다."}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/law-mappings/{mapping_id}")
async def delete_law_mapping(
    mapping_id: int,
    db: AsyncSession = Depends(get_db),
):
    """조례-법령 매핑 삭제"""
    service = OrdinanceService(db)
    try:
        await service.delete_law_mapping(mapping_id)
        return {"success": True, "message": "삭제되었습니다."}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
