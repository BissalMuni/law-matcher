"""
Article (조문) model
"""
from datetime import datetime, date
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Text, Date, DateTime, Integer, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base

if TYPE_CHECKING:
    from backend.models.law import Law
    from backend.models.ordinance_article_mapping import OrdinanceArticleMapping
    from backend.models.article_change import ArticleChange


class Article(Base):
    """
    법령 조문 테이블

    법제처 lawService API 응답의 조문 정보 기반
    """
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    law_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("laws.id", ondelete="CASCADE"),
        nullable=False
    )

    # 조문 식별
    article_no: Mapped[str] = mapped_column(String(50), nullable=False)
    article_title: Mapped[Optional[str]] = mapped_column(String(500))

    # 조문 내용
    article_content: Mapped[str] = mapped_column(Text, nullable=False)
    paragraphs: Mapped[Optional[dict]] = mapped_column(JSONB)

    # 변경 감지용
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # 법제처 API 원본 정보
    mst_seq: Mapped[Optional[int]] = mapped_column(Integer)
    jo_seq: Mapped[Optional[int]] = mapped_column(Integer)

    # 메타데이터
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationships
    law: Mapped["Law"] = relationship(back_populates="articles")
    ordinance_mappings: Mapped[List["OrdinanceArticleMapping"]] = relationship(
        back_populates="article",
        cascade="all, delete-orphan"
    )
    changes: Mapped[List["ArticleChange"]] = relationship(
        back_populates="article",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index('idx_articles_law_id', 'law_id'),
        Index('idx_articles_content_hash', 'content_hash'),
        Index('idx_articles_article_no', 'article_no'),
        Index('idx_articles_last_synced', 'last_synced_at'),
    )

    def __repr__(self) -> str:
        return f"<Article(id={self.id}, law_id={self.law_id}, no={self.article_no})>"
