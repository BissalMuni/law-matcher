"""
Ordinance-Law mapping model (조례-상위법령 연계)
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base

if TYPE_CHECKING:
    from backend.models.ordinance import Ordinance
    from backend.models.law import Law


class OrdinanceLawMapping(Base):
    """
    조례-상위법령 연계 테이블 (N:M 관계)

    하나의 조례는 여러 상위법령과 연결될 수 있고,
    하나의 상위법령은 여러 조례와 연결될 수 있음
    """
    __tablename__ = "ordinance_law_mappings"

    __table_args__ = (
        UniqueConstraint('ordinance_id', 'law_id', name='uq_ordinance_law'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    # Foreign Keys
    ordinance_id: Mapped[int] = mapped_column(
        ForeignKey("ordinances.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    law_id: Mapped[int] = mapped_column(
        ForeignKey("laws.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # 연계 상세 정보
    related_articles: Mapped[Optional[str]] = mapped_column(String(500))  # 관련 조문 (예: "제3조, 제5조")

    # 메타 정보
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    ordinance: Mapped["Ordinance"] = relationship(back_populates="law_mappings")
    law: Mapped["Law"] = relationship(back_populates="ordinance_mappings")

    def __repr__(self) -> str:
        return f"<OrdinanceLawMapping(ordinance_id={self.ordinance_id}, law_id={self.law_id})>"
