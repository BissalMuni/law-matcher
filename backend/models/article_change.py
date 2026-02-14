"""
ArticleChange (조문 변경 이력) model
"""
from datetime import datetime, date
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, Date, DateTime, Integer, ForeignKey, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base

if TYPE_CHECKING:
    from backend.models.article import Article


class ArticleChange(Base):
    """
    조문 변경 이력 테이블

    조문의 개정 이력을 추적하여 영향받는 조례를 파악
    """
    __tablename__ = "article_changes"

    id: Mapped[int] = mapped_column(primary_key=True)
    article_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False
    )

    # 변경 정보
    change_date: Mapped[date] = mapped_column(Date, nullable=False)
    change_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # 변경 내용
    old_content: Mapped[Optional[str]] = mapped_column(Text)
    new_content: Mapped[Optional[str]] = mapped_column(Text)
    old_hash: Mapped[Optional[str]] = mapped_column(String(64))
    new_hash: Mapped[Optional[str]] = mapped_column(String(64))

    # diff 정보
    diff_html: Mapped[Optional[str]] = mapped_column(Text)

    # 감지 정보
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    notified: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    article: Mapped["Article"] = relationship(back_populates="changes")

    __table_args__ = (
        Index('idx_article_changes_article_id', 'article_id'),
        Index('idx_article_changes_change_date', 'change_date'),
        Index('idx_article_changes_detected_at', 'detected_at'),
        Index('idx_article_changes_notified', 'notified'),
    )

    def __repr__(self) -> str:
        return f"<ArticleChange(id={self.id}, article_id={self.article_id}, type={self.change_type})>"
