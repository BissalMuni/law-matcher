"""
Ordinance models
"""
from datetime import datetime, date
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Text, Date, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base

if TYPE_CHECKING:
    from backend.models.department import Department
    from backend.models.ordinance_law_mapping import OrdinanceLawMapping


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
    articles: Mapped[List["OrdinanceArticle"]] = relationship(
        back_populates="ordinance", cascade="all, delete-orphan"
    )
    # 새로운 구조: laws 테이블과 N:M 관계
    law_mappings: Mapped[List["OrdinanceLawMapping"]] = relationship(
        back_populates="ordinance", cascade="all, delete-orphan"
    )
    reviews: Mapped[List["AmendmentReview"]] = relationship(
        back_populates="ordinance"
    )


class OrdinanceArticle(Base):
    """자치법규 조문"""
    __tablename__ = "ordinance_articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    ordinance_id: Mapped[int] = mapped_column(ForeignKey("ordinances.id"))
    article_no: Mapped[str] = mapped_column(String(20), nullable=False)
    paragraph_no: Mapped[Optional[str]] = mapped_column(String(20))
    item_no: Mapped[Optional[str]] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    ordinance: Mapped["Ordinance"] = relationship(back_populates="articles")
