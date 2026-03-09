"""
조례 전문(본문) 캐시 모델 - 법제처 API에서 가져온 조례 조문 저장
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, DateTime, Integer, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base

if TYPE_CHECKING:
    from backend.models.ordinance import Ordinance


class OrdinanceText(Base):
    """조례 전문(본문) 캐시 테이블"""
    __tablename__ = "ordinance_texts"

    id: Mapped[int] = mapped_column(primary_key=True)
    ordinance_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ordinances.id", ondelete="CASCADE"),
        nullable=False,
    )
    serial_no: Mapped[str] = mapped_column(String(50), nullable=False)  # 자치법규일련번호
    full_text: Mapped[Optional[str]] = mapped_column(Text)  # 전체 조문 텍스트
    articles_json: Mapped[Optional[dict]] = mapped_column(JSONB)  # 조문별 구조화 데이터
    fetched_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationships
    ordinance: Mapped[Optional["Ordinance"]] = relationship(back_populates="ordinance_text")

    __table_args__ = (
        UniqueConstraint("ordinance_id", name="uq_ordinance_texts_ordinance_id"),
        Index("idx_ordinance_texts_fetched_at", "fetched_at"),
    )
