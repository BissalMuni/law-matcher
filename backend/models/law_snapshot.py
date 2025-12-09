"""
Law Snapshot model
"""
from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Integer, Date, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


class LawSnapshot(Base):
    """법령 스냅샷"""
    __tablename__ = "law_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    law_id: Mapped[str] = mapped_column(String(50), nullable=False)
    law_mst: Mapped[str] = mapped_column(String(50), nullable=False)
    law_name: Mapped[str] = mapped_column(String(500), nullable=False)
    law_type: Mapped[str] = mapped_column(String(20), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    proclaimed_date: Mapped[Optional[date]] = mapped_column(Date)
    enforced_date: Mapped[Optional[date]] = mapped_column(Date)
    revision_type: Mapped[Optional[str]] = mapped_column(String(50))
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
