"""
OrdinanceArticleMapping (조례-조문 연계) model
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, DateTime, Integer, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base

if TYPE_CHECKING:
    from backend.models.ordinance import Ordinance
    from backend.models.article import Article
    from backend.models.user import User


class OrdinanceArticleMapping(Base):
    """
    조례-조문 연계 테이블

    특정 조례가 어느 법령의 어느 조문과 연계되는지 관리
    """
    __tablename__ = "ordinance_article_mappings"

    id: Mapped[int] = mapped_column(primary_key=True)
    ordinance_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ordinances.id", ondelete="CASCADE"),
        nullable=False
    )
    article_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False
    )

    # 연계 정보
    mapping_reason: Mapped[Optional[str]] = mapped_column(Text)
    related_article_nos: Mapped[Optional[str]] = mapped_column(String(200))

    # 추적 정보
    created_by: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationships
    ordinance: Mapped["Ordinance"] = relationship(back_populates="article_mappings")
    article: Mapped["Article"] = relationship(back_populates="ordinance_mappings")
    creator: Mapped[Optional["User"]] = relationship()

    __table_args__ = (
        Index('idx_ordinance_article_mappings_ordinance_id', 'ordinance_id'),
        Index('idx_ordinance_article_mappings_article_id', 'article_id'),
    )

    def __repr__(self) -> str:
        return f"<OrdinanceArticleMapping(ord={self.ordinance_id}, art={self.article_id})>"
