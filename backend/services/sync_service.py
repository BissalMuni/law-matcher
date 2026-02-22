"""
Law Sync Service
"""
from typing import Optional, List
from celery.result import AsyncResult
from sqlalchemy.ext.asyncio import AsyncSession

from backend.celery_app import celery_app
from backend.tasks import sync_laws


class SyncService:
    """Law synchronization service"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def start_sync(
        self,
        law_ids: Optional[List[str]],
    ) -> str:
        """Start sync task"""
        task = sync_laws.delay(law_ids)
        return task.id

    async def get_status(self, task_id: Optional[str] = None) -> dict:
        """Get sync status"""
        if not task_id:
            return {
                "task_id": None,
                "status": "IDLE",
                "total": 0,
                "synced": 0,
                "failed": 0,
            }

        result: AsyncResult = celery_app.AsyncResult(task_id)
        state = result.state
        status_map = {
            "PENDING": "PENDING",
            "RECEIVED": "RUNNING",
            "STARTED": "RUNNING",
            "RETRY": "RUNNING",
            "SUCCESS": "COMPLETED",
            "FAILURE": "FAILED",
            "REVOKED": "FAILED",
        }

        payload = result.result if isinstance(result.result, dict) else {}
        total = payload.get("total_laws", 0) if state == "SUCCESS" else 0
        synced = payload.get("updated", 0) if state == "SUCCESS" else 0
        failed = payload.get("failed", 0) if state == "SUCCESS" else 0

        return {
            "task_id": task_id,
            "status": status_map.get(state, state),
            "total": total,
            "synced": synced,
            "failed": failed,
        }
