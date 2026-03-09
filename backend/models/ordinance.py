"""
Ordinance models
"""
from datetime import datetime, date
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Date, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base

if TYPE_CHECKING:
    from backend.models.department import Department
    from backend.models.ordinance_law_mapping import OrdinanceLawMapping
    from backend.models.ordinance_review import OrdinanceReview
    from backend.models.ordinance_text import OrdinanceText


class Ordinance(Base):
    """자치법규 (조례/규칙)"""
    __tablename__ = "ordinances"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # 자치법규ID
    name: Mapped[str] = mapped_column(String(500), nullable=False)  # 자치법규명
    category: Mapped[Optional[str]] = mapped_column(String(100))  # 자치법규종류 (조례/규칙)
    department: Mapped[Optional[str]] = mapped_column(String(200))
    department_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("departments.id"), nullable=True
    )
    enacted_date: Mapped[Optional[date]] = mapped_column(Date)  # 공포일자
    enforced_date: Mapped[Optional[date]] = mapped_column(Date)  # 시행일자
    revision_date: Mapped[Optional[date]] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    no_parent_law: Mapped[bool] = mapped_column(default=False)  # 상위법령 없음 확인 여부
    revision_status: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, index=True
    )  # 검토 상태: null/검토대기/검토중/개정확정

    @property
    def has_revision_flag(self) -> bool:
        """빨간불 표시 여부 (revision_status가 null이 아니면 빨간불)"""
        return self.revision_status is not None

    # 법제처 API 추가 필드
    serial_no: Mapped[Optional[str]] = mapped_column(String(50))  # 자치법규일련번호
    field_name: Mapped[Optional[str]] = mapped_column(String(200))  # 자치법규분야명
    org_name: Mapped[Optional[str]] = mapped_column(String(200))  # 지자체기관명
    promulgation_no: Mapped[Optional[str]] = mapped_column(String(50))  # 공포번호
    revision_type: Mapped[Optional[str]] = mapped_column(String(50))  # 제개정구분명
    detail_link: Mapped[Optional[str]] = mapped_column(String(500))  # 자치법규상세링크
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    department_rel: Mapped[Optional["Department"]] = relationship(
        back_populates="ordinances"
    )
    # 새로운 구조: laws 테이블과 N:M 관계
    law_mappings: Mapped[List["OrdinanceLawMapping"]] = relationship(
        back_populates="ordinance", cascade="all, delete-orphan"
    )
    reviews: Mapped[List["AmendmentReview"]] = relationship(
        back_populates="ordinance"
    )
    ordinance_reviews: Mapped[List["OrdinanceReview"]] = relationship(
        back_populates="ordinance", cascade="all, delete-orphan"
    )
    ordinance_text: Mapped[Optional["OrdinanceText"]] = relationship(
        back_populates="ordinance", uselist=False, cascade="all, delete-orphan"
    )
