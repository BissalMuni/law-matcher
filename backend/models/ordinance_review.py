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
    from backend.models.user import User


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

    # 작성자 및 수정자 추적 (User FK)
    created_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL")
    )
    updated_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL")
    )

    # 관리자 승인
    approval_status: Mapped[Optional[str]] = mapped_column(
        String(20), default="pending"  # pending, approved, rejected
    )
    approved_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL")
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    approval_note: Mapped[Optional[str]] = mapped_column(Text)  # 승인/반려 사유

    # 타임스탬프
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    ordinance: Mapped["Ordinance"] = relationship(back_populates="ordinance_reviews")
    created_by: Mapped[Optional["User"]] = relationship(
        back_populates="created_reviews", foreign_keys=[created_by_id]
    )
    updated_by: Mapped[Optional["User"]] = relationship(
        back_populates="updated_reviews", foreign_keys=[updated_by_id]
    )
    approved_by: Mapped[Optional["User"]] = relationship(
        foreign_keys=[approved_by_id]
    )

    def __repr__(self) -> str:
        return f"<OrdinanceReview(id={self.id}, ordinance_id={self.ordinance_id}, reviewer_type={self.reviewer_type})>"
