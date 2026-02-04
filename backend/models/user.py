"""
User model - 사용자 정보
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base

if TYPE_CHECKING:
    from backend.models.department import Department
    from backend.models.ordinance_review import OrdinanceReview


class User(Base):
    """사용자"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(100))
    user_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # "DEPARTMENT" | "GENERAL"
    department_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("departments.id", ondelete="SET NULL")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    department: Mapped[Optional["Department"]] = relationship(back_populates="users")
    created_reviews: Mapped[list["OrdinanceReview"]] = relationship(
        back_populates="created_by", foreign_keys="OrdinanceReview.created_by_id"
    )
    updated_reviews: Mapped[list["OrdinanceReview"]] = relationship(
        back_populates="updated_by", foreign_keys="OrdinanceReview.updated_by_id"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, user_type={self.user_type})>"
