"""
Law revision reason model
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, DateTime, Integer, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base

if TYPE_CHECKING:
    from backend.models.law import Law


class LawRevisionReason(Base):
    """법령 제개정이유 캐시 테이블"""
    __tablename__ = "law_revision_reasons"

    id: Mapped[int] = mapped_column(primary_key=True)
    law_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("laws.id", ondelete="CASCADE"),
        nullable=False,
    )
    law_mst: Mapped[str] = mapped_column(String(30), nullable=False)
    revision_reason: Mapped[Optional[str]] = mapped_column(Text)
    amendment_content: Mapped[Optional[str]] = mapped_column(Text)
    extracted_articles: Mapped[Optional[dict]] = mapped_column(JSONB)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationships
    law: Mapped[Optional["Law"]] = relationship(back_populates="revision_reason")

    __table_args__ = (
        UniqueConstraint("law_id", name="uq_law_revision_reasons_law_id"),
        Index("idx_law_revision_reasons_fetched_at", "fetched_at"),
    )
