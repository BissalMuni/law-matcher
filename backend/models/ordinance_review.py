"""
Ordinance Review models - 자치법규 검토이력
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base

if TYPE_CHECKING:
    from backend.models.ordinance import Ordinance


class OrdinanceReview(Base):
    """자치법규 검토이력"""
    __tablename__ = "ordinance_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    ordinance_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ordinances.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # 검토자 정보
    reviewer_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "DEPARTMENT" | "GENERAL"
    reviewer_name: Mapped[Optional[str]] = mapped_column(String(100))  # 검토자명
    reviewer_department: Mapped[Optional[str]] = mapped_column(String(200))  # 검토자 소속부서

    # 검토 내용
    review_content: Mapped[str] = mapped_column(Text, nullable=False)  # 검토의견
    review_result: Mapped[Optional[str]] = mapped_column(String(50))  # 검토결과: 개정필요/개정불필요/검토중/보류

    # 타임스탬프
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    ordinance: Mapped["Ordinance"] = relationship(back_populates="ordinance_reviews")

    def __repr__(self) -> str:
        return f"<OrdinanceReview(id={self.id}, ordinance_id={self.ordinance_id}, reviewer_type={self.reviewer_type})>"
