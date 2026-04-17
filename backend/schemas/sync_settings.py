"""
SyncSettings schemas - 법령 자동 동기화 설정 DTO
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class SyncSettingsResponse(BaseModel):
    auto_sync_enabled: bool
    interval_hours: int
    last_sync_at: Optional[datetime]
    next_sync_at: Optional[datetime]
    updated_at: datetime
    updated_by: Optional[int]


class SyncSettingsUpdate(BaseModel):
    auto_sync_enabled: Optional[bool] = None
    interval_hours: Optional[int] = Field(None, ge=1, le=720)  # 1시간 ~ 30일
