"""
Law Amendment model
"""
from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, Date, ForeignKey, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base


class LawAmendment(Base):
    """법령 개정 감지 및 조례 개정 대상"""
    __tablename__ = "law_amendments"

    id: Mapped[int] = mapped_column(primary_key=True)

    # 조례 연결 (개정 대상)
    ordinance_id: Mapped[Optional[int]] = mapped_column(ForeignKey("ordinances.id"), nullable=True)

    # 상위법령 정보 (기존 필드 유지 + 새 필드)
    law_id: Mapped[str] = mapped_column(String(50), nullable=False)  # 기존 호환용
    law_name: Mapped[str] = mapped_column(String(500), nullable=False)

    # 새 구조: laws 테이블과 연결
    source_law_id: Mapped[Optional[int]] = mapped_column(ForeignKey("laws.id"), nullable=True)
    source_law_name: Mapped[Optional[str]] = mapped_column(String(500))  # 편의용
    source_proclaimed_date: Mapped[Optional[date]] = mapped_column(Date)  # 개정 공포일

    # 스냅샷 (기존 유지)
    old_snapshot_id: Mapped[Optional[int]] = mapped_column(ForeignKey("law_snapshots.id"))
    new_snapshot_id: Mapped[Optional[int]] = mapped_column(ForeignKey("law_snapshots.id"))

    # 개정 정보
    change_type: Mapped[str] = mapped_column(String(50), nullable=False)  # REVISION/ENACTED/ABOLISHED
    description: Mapped[Optional[str]] = mapped_column(String(1000))  # 개정 설명
    change_summary: Mapped[Optional[dict]] = mapped_column(JSON)

    # 상태 관리
    status: Mapped[str] = mapped_column(String(20), default="PENDING")  # PENDING/REVIEWED/COMPLETED
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    reviews: Mapped[list["AmendmentReview"]] = relationship(back_populates="amendment")
    ordinance: Mapped[Optional["Ordinance"]] = relationship()
    source_law: Mapped[Optional["Law"]] = relationship()
