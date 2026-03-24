"""
Batch processing job model - 일괄 개정검토 작업
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, Integer, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base


class BatchJob(Base):
    """일괄 개정검토 작업 (전체 배치)"""
    __tablename__ = "batch_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)  # 작업명 (예: "2026-03 전체 조례 개정검토")
    created_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL")
    )

    # 현재 진행 단계: step1_select / step2_detect / step3_collect / step4_analyze / step5_report
    current_step: Mapped[str] = mapped_column(String(30), default="step1_select", nullable=False)

    # 각 단계 상태: idle / running / completed / failed
    step1_status: Mapped[str] = mapped_column(String(20), default="completed", nullable=False)
    step2_status: Mapped[str] = mapped_column(String(20), default="idle", nullable=False)
    step3_status: Mapped[str] = mapped_column(String(20), default="idle", nullable=False)
    step4_status: Mapped[str] = mapped_column(String(20), default="idle", nullable=False)
    step5_status: Mapped[str] = mapped_column(String(20), default="idle", nullable=False)

    # 각 단계 진행률
    step2_progress: Mapped[int] = mapped_column(Integer, default=0)
    step2_total: Mapped[int] = mapped_column(Integer, default=0)
    step3_progress: Mapped[int] = mapped_column(Integer, default=0)
    step3_total: Mapped[int] = mapped_column(Integer, default=0)
    step4_progress: Mapped[int] = mapped_column(Integer, default=0)
    step4_total: Mapped[int] = mapped_column(Integer, default=0)

    # 필터 조건 저장 (Step 1에서 설정한 필터)
    filter_params: Mapped[Optional[dict]] = mapped_column(JSONB)

    # 통계 요약
    summary: Mapped[Optional[dict]] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    items: Mapped[list["BatchJobItem"]] = relationship(back_populates="batch_job", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_batch_jobs_created_at", "created_at"),
    )


class BatchJobItem(Base):
    """일괄 작업 개별 항목 - 각 조례의 단계별 상태 추적"""
    __tablename__ = "batch_job_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_job_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("batch_jobs.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    ordinance_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ordinances.id", ondelete="CASCADE"),
        nullable=False
    )

    # 조례 기본 정보 (스냅샷 — 조회 편의용)
    ordinance_name: Mapped[str] = mapped_column(String(500), nullable=False)
    ordinance_department: Mapped[Optional[str]] = mapped_column(String(200))
    ordinance_category: Mapped[Optional[str]] = mapped_column(String(100))

    # Step 1: 대상 선정 — included / excluded
    step1_result: Mapped[str] = mapped_column(String(20), default="included", nullable=False)
    step1_reason: Mapped[Optional[str]] = mapped_column(String(200))  # 제외 사유

    # Step 2: 개정판별 — pending / needs_revision / no_revision / error
    step2_result: Mapped[Optional[str]] = mapped_column(String(30))
    step2_reason: Mapped[Optional[str]] = mapped_column(String(500))
    step2_detail: Mapped[Optional[dict]] = mapped_column(JSONB)  # 판별 상세 정보

    # Step 3: 제개정이유 수집 — pending / collected / no_data / error
    step3_result: Mapped[Optional[str]] = mapped_column(String(30))
    step3_reason: Mapped[Optional[str]] = mapped_column(String(500))

    # Step 4: AI 분석 — pending / needs_revision / no_revision / error
    step4_result: Mapped[Optional[str]] = mapped_column(String(30))
    step4_reason: Mapped[Optional[str]] = mapped_column(String(500))
    step4_ai_summary: Mapped[Optional[str]] = mapped_column(Text)  # AI 분석 요약
    step4_ai_result: Mapped[Optional[str]] = mapped_column(String(20))  # 개정필요 / 개정불필요

    # 최종 결과: 개정필요 / 개정불필요 / 해당없음 / 수동확인필요 / 오류 / 제외
    final_result: Mapped[Optional[str]] = mapped_column(String(30))

    # 관리자 수동 제외 여부
    manually_excluded: Mapped[bool] = mapped_column(default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    batch_job: Mapped["BatchJob"] = relationship(back_populates="items")

    __table_args__ = (
        Index("idx_batch_job_items_batch_ordinance", "batch_job_id", "ordinance_id", unique=True),
    )
