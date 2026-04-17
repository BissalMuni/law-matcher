"""
SyncSettings model - 법령 자동 동기화 설정
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


class SyncSettings(Base):
    """법령 동기화 설정 (싱글턴 행)"""
    __tablename__ = "sync_settings"

    id: Mapped[int] = mapped_column(primary_key=True)  # 항상 1
    auto_sync_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    interval_hours: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    next_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    updated_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<SyncSettings(auto={self.auto_sync_enabled}, interval={self.interval_hours}h)>"
