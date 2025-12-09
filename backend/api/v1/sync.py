"""
Law Sync API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db
from backend.schemas.sync import SyncRequest, SyncResponse, SyncStatusResponse
from backend.services.sync_service import SyncService

router = APIRouter()


@router.post("/laws", response_model=SyncResponse, status_code=202)
async def sync_laws(
    request: SyncRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Start law synchronization task"""
    service = SyncService(db)
    task_id = await service.start_sync(request.law_ids, background_tasks)
    return SyncResponse(task_id=task_id, status="PENDING")


@router.post("/laws/{law_id}", response_model=SyncResponse, status_code=202)
async def sync_single_law(
    law_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Sync a specific law"""
    service = SyncService(db)
    task_id = await service.start_sync([law_id], background_tasks)
    return SyncResponse(task_id=task_id, status="PENDING")


@router.get("/status", response_model=SyncStatusResponse)
async def get_sync_status(
    task_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get synchronization status"""
    service = SyncService(db)
    return await service.get_status(task_id)
