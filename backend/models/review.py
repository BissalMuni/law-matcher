"""
Amendment Review model
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base


class AmendmentReview(Base):
    """개정 검토 결과"""
    __tablename__ = "amendment_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    amendment_id: Mapped[int] = mapped_column(ForeignKey("law_amendments.id"))
    ordinance_id: Mapped[int] = mapped_column(ForeignKey("ordinances.id"))
    need_revision: Mapped[bool] = mapped_column(Boolean, nullable=False)
    revision_urgency: Mapped[Optional[str]] = mapped_column(String(20))  # HIGH/MEDIUM/LOW
    affected_articles: Mapped[Optional[dict]] = mapped_column(JSON)
    reason: Mapped[Optional[str]] = mapped_column(Text)
    recommendation: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")  # PENDING/REVIEWED/COMPLETED
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(100))
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    amendment: Mapped["LawAmendment"] = relationship(back_populates="reviews")
    ordinance: Mapped["Ordinance"] = relationship(back_populates="reviews")
