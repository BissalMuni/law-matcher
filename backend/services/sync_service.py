"""
Law Sync Service
"""
import uuid
from typing import Optional, List
from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from backend.external.moleg_client import MolegClient
from backend.core.config import settings


class SyncService:
    """Law synchronization service"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.moleg_client = MolegClient(
            api_key=settings.MOLEG_API_KEY,
            base_url=settings.MOLEG_API_BASE_URL,
        )

    async def start_sync(
        self,
        law_ids: Optional[List[str]],
        background_tasks: BackgroundTasks,
    ) -> str:
        """Start sync task"""
        task_id = str(uuid.uuid4())

        # Add background task
        background_tasks.add_task(
            self._run_sync,
            task_id=task_id,
            law_ids=law_ids,
        )

        return task_id

    async def _run_sync(
        self,
        task_id: str,
        law_ids: Optional[List[str]],
    ):
        """Run sync in background"""
        # TODO: Implement actual sync logic
        # 1. Get parent laws from DB
        # 2. Fetch from MOLEG API
        # 3. Compare and detect changes
        # 4. Save snapshots and amendments
        pass

    async def get_status(self, task_id: Optional[str] = None) -> dict:
        """Get sync status"""
        # TODO: Implement with Redis or DB
        return {
            "task_id": task_id,
            "status": "IDLE",
            "total": 0,
            "synced": 0,
            "failed": 0,
        }
