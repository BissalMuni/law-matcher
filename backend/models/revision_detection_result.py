"""
Revision detection result model
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Integer, ForeignKey, Boolean, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


class RevisionDetectionResult(Base):
    """조례-법령 개정 판별 결과"""
    __tablename__ = "revision_detection_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    ordinance_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ordinances.id", ondelete="CASCADE"),
        nullable=False,
    )
    law_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("laws.id", ondelete="CASCADE"),
        nullable=False,
    )
    detection_method: Mapped[str] = mapped_column(String(30), nullable=False)
    needs_revision: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    detail: Mapped[Optional[dict]] = mapped_column(JSONB)
    detected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    __table_args__ = (
        UniqueConstraint(
            "ordinance_id",
            "law_id",
            "detection_method",
            name="uq_revision_detection_result",
        ),
        Index("idx_revision_detection_results_ordinance_id", "ordinance_id"),
        Index("idx_revision_detection_results_detection_method", "detection_method"),
    )
