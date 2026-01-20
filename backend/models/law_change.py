"""
LawChange model - 법령 변경 이력 관리
동기화 시 감지된 법령 변경사항을 저장하고 부서별로 관리
"""
from datetime import datetime, date
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, Date, DateTime, Integer, BigInteger, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from backend.core.database import Base

if TYPE_CHECKING:
    from backend.models.law import Law
    from backend.models.department import Department


class ChangeStatus(str, enum.Enum):
    """변경사항 처리 상태"""
    PENDING = "pending"          # 대기 (검토 필요)
    REVIEWING = "reviewing"      # 검토 중
    APPROVED = "approved"        # 승인됨 (laws 테이블 업데이트 완료)
    REJECTED = "rejected"        # 반려됨 (변경사항 무시)


class ApiStatus(str, enum.Enum):
    """API 응답 상태"""
    SUCCESS = "success"          # API 성공, 정확히 일치하는 법령 발견
    NO_RESPONSE = "no_response"  # API 응답 없음
    NOT_FOUND = "not_found"      # API 응답은 있으나 정확히 일치하는 법령명 없음


class LawChange(Base):
    """
    법령 변경 이력 테이블

    동기화 시 감지된 변경사항을 저장하고,
    부서 담당자가 검토 후 laws 테이블에 반영할 수 있도록 관리
    """
    __tablename__ = "law_changes"

    id: Mapped[int] = mapped_column(primary_key=True)

    # 법령 참조
    law_id: Mapped[int] = mapped_column(ForeignKey("laws.id"), nullable=False, index=True)

    # 동기화 정보
    sync_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)  # 동기화 실시 일자
    sync_batch_id: Mapped[Optional[str]] = mapped_column(String(50), index=True)  # 동기화 배치 ID (같은 배치로 묶기)

    # API 응답 상태
    api_status: Mapped[ApiStatus] = mapped_column(
        SQLEnum(ApiStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ApiStatus.SUCCESS
    )
    api_message: Mapped[Optional[str]] = mapped_column(String(500))

    # 변경 전 값 (JSON)
    old_values: Mapped[Optional[dict]] = mapped_column(JSON)
    # {
    #   "proclaimed_date": "2024-01-01",
    #   "enforced_date": "2024-03-01",
    #   "revision_type": "일부개정",
    #   "law_id": 123456
    # }

    # 변경 후 값 (JSON) - API에서 받은 새로운 값
    new_values: Mapped[Optional[dict]] = mapped_column(JSON)

    # 부서 정보 (소관부처)
    dept_name: Mapped[Optional[str]] = mapped_column(String(200), index=True)  # 소관부처명
    dept_code: Mapped[Optional[int]] = mapped_column(Integer)  # 소관부처코드

    # 처리 상태
    status: Mapped[ChangeStatus] = mapped_column(
        SQLEnum(ChangeStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ChangeStatus.PENDING,
        index=True
    )

    # 처리 정보
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)  # 처리 일시
    processed_by: Mapped[Optional[str]] = mapped_column(String(100))  # 처리자
    process_note: Mapped[Optional[str]] = mapped_column(Text)  # 처리 메모

    # 타임스탬프
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    law: Mapped["Law"] = relationship("Law", backref="changes")

    def __repr__(self) -> str:
        return f"<LawChange(id={self.id}, law_id={self.law_id}, status={self.status})>"
