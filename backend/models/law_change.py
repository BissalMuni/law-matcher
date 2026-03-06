"""
LawChange model - 법령 변경 감지 로그
동기화 시 감지된 법령 변경사항을 기록 (감지 로그 전용, 승인/반려 워크플로우 없음)
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, DateTime, Integer, ForeignKey, Enum as SQLEnum, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from backend.core.database import Base

if TYPE_CHECKING:
    from backend.models.law import Law


class ApiStatus(str, enum.Enum):
    """API 응답 상태"""
    SUCCESS = "success"          # API 성공, 정확히 일치하는 법령 발견
    NO_RESPONSE = "no_response"  # API 응답 없음
    NOT_FOUND = "not_found"      # API 응답은 있으나 정확히 일치하는 법령명 없음


class LawChange(Base):
    """
    법령 변경 감지 로그 테이블

    동기화 시 감지된 변경사항을 기록한다.
    감지 로그 전용이며, 승인/반려 워크플로우는 없다.
    """
    __tablename__ = "law_changes"
    __table_args__ = (
        UniqueConstraint('law_id', 'sync_batch_id', name='uq_law_changes_law_batch'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    # 법령 참조
    law_id: Mapped[int] = mapped_column(ForeignKey("laws.id"), nullable=False, index=True)

    # 동기화 정보
    sync_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    sync_batch_id: Mapped[Optional[str]] = mapped_column(String(50), index=True)

    # API 응답 상태
    api_status: Mapped[ApiStatus] = mapped_column(
        SQLEnum(ApiStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ApiStatus.SUCCESS
    )
    api_message: Mapped[Optional[str]] = mapped_column(String(500))

    # 변경 전/후 값 (JSON)
    old_values: Mapped[Optional[dict]] = mapped_column(JSON)
    new_values: Mapped[Optional[dict]] = mapped_column(JSON)

    # 부서 정보 (소관부처)
    dept_name: Mapped[Optional[str]] = mapped_column(String(200), index=True)
    dept_code: Mapped[Optional[int]] = mapped_column(Integer)

    # 타임스탬프
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    law: Mapped["Law"] = relationship("Law", backref="changes")

    def __repr__(self) -> str:
        return f"<LawChange(id={self.id}, law_id={self.law_id}, api_status={self.api_status})>"
