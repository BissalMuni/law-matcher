"""등록 조례/상위법령 연동 엔드포인트 (Phase 3 핵심).

실시간 법제처 API 대신 law-matcher에 등록된 조례를 입안심사 소스로 제공한다.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db
from backend.drafting.service import DraftingService

router = APIRouter()


@router.get("/source-ordinances")
async def list_source_ordinances(
    query: Optional[str] = Query(None, description="조례명 검색어"),
    limit: int = Query(30, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """입안심사 시작에 쓸 등록 조례 후보 목록."""
    service = DraftingService(db)
    return {"ordinances": await service.list_source_ordinances(query, limit)}


@router.get("/source-ordinances/{ordinance_id}/preview")
async def preview_source_ordinance(
    ordinance_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """등록 조례 미리보기 — 조문 + 상위법령 (입안심사 시작 전 확인용)."""
    service = DraftingService(db)
    result = await service.preview_source_ordinance(ordinance_id)
    if not result.get("found"):
        raise HTTPException(status_code=404, detail="조례를 찾을 수 없습니다.")
    return result


@router.get("/source-ordinances/{ordinance_id}/parent-laws")
async def get_parent_laws(
    ordinance_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """조례의 상위법령 목록 (AI 컨텍스트·UI 표시용)."""
    service = DraftingService(db)
    return {"parent_laws": await service.get_parent_laws(ordinance_id)}
