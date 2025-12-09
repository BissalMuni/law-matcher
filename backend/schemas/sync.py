"""
Sync schemas
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


class SyncRequest(BaseModel):
    """Sync request"""
    law_ids: Optional[List[str]] = None  # Empty = sync all


class SyncResponse(BaseModel):
    """Sync response"""
    task_id: str
    status: str  # PENDING, RUNNING, COMPLETED, FAILED


class SyncStatusResponse(BaseModel):
    """Sync status response"""
    task_id: Optional[str] = None
    status: str
    total: int = 0
    synced: int = 0
    failed: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
