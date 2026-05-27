"""
입안심사(drafting) 모델 — law-ebansimsa 통합

law-ebansimsa의 Prisma 스키마(Project/Stage/OrdinanceSection/Message/
ValidationResult/Reference/Snapshot)를 SQLAlchemy로 이관한 신규 테이블 집합.

원칙(통합 계획 docs/ebansimsa-integration-plan.md):
- 모든 테이블은 `drafting_` 접두사를 쓰는 신규 테이블 (additive)
- 기존 ordinances/laws 스키마는 변경하지 않고 FK로만 참조
- SQL 예약어 회피: Prisma `order` → `sort_order`, `trigger` → `trigger_type`
"""
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import (
    String,
    Text,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base

if TYPE_CHECKING:
    from backend.models.ordinance import Ordinance


class DraftingProject(Base):
    """입안 프로젝트 — 한 건의 조례 제정/개정 작업 단위 (Prisma Project)"""
    __tablename__ = "drafting_projects"

    id: Mapped[int] = mapped_column(primary_key=True)

    # 개정 모드: law-matcher에 등록된 조례에서 시작 (실시간 법제처 API 치환)
    ordinance_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("ordinances.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # enact|amend_partial|amend_full
    title: Mapped[str] = mapped_column(String(500), nullable=False)  # 제명
    municipality: Mapped[str] = mapped_column(String(200), nullable=False)  # 지자체명
    source_url: Mapped[Optional[str]] = mapped_column(String(500))  # 개정 모드 원문 출처
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)  # active|locked
    progress: Mapped[int] = mapped_column(Integer, default=0)  # 0-100 파생 캐시

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships (drafting 내부에 한정 — 기존 모델 무손상)
    ordinance: Mapped[Optional["Ordinance"]] = relationship(viewonly=True)
    stages: Mapped[List["DraftingStage"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    sections: Mapped[List["DraftingSection"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    references: Mapped[List["DraftingReference"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class DraftingStage(Base):
    """표준 8단계 + 본칙 동적 sub-stage (Prisma Stage, self-relation)"""
    __tablename__ = "drafting_stages"

    __table_args__ = (
        UniqueConstraint("project_id", "key", "parent_id", name="uq_drafting_stage_key"),
        Index("idx_drafting_stages_project_order", "project_id", "sort_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("drafting_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String(50), nullable=False)
    # meta|purpose|definition|scope|main|supplementary|review|finalize
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(20), default="locked")
    # locked|available|in_progress|validating|confirmed|stale|failed
    stale_reason: Mapped[Optional[str]] = mapped_column(Text)
    wiki_ref: Mapped[Optional[str]] = mapped_column(String(50))  # 근거 위키 섹션 (예: 2.1.4)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 본칙 동적 sub-stage (self-FK)
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("drafting_stages.id", ondelete="CASCADE"), nullable=True
    )

    # Relationships
    project: Mapped["DraftingProject"] = relationship(back_populates="stages")
    substages: Mapped[List["DraftingStage"]] = relationship(
        back_populates="parent", cascade="all, delete-orphan"
    )
    parent: Mapped[Optional["DraftingStage"]] = relationship(
        back_populates="substages", remote_side="DraftingStage.id"
    )
    sections: Mapped[List["DraftingSection"]] = relationship(
        back_populates="stage", cascade="all, delete-orphan"
    )
    messages: Mapped[List["DraftingMessage"]] = relationship(
        back_populates="stage", cascade="all, delete-orphan"
    )
    snapshots: Mapped[List["DraftingSnapshot"]] = relationship(
        back_populates="stage", cascade="all, delete-orphan"
    )


class DraftingSection(Base):
    """조(條) 단위 본문. 개정 모드는 original_body 보유 (Prisma OrdinanceSection)"""
    __tablename__ = "drafting_sections"

    __table_args__ = (
        Index("idx_drafting_sections_project_order", "project_id", "sort_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("drafting_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stage_id: Mapped[int] = mapped_column(
        ForeignKey("drafting_stages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    article_no: Mapped[int] = mapped_column(Integer, nullable=False)  # 조 번호 (제N조)
    article_label: Mapped[Optional[str]] = mapped_column(String(200))  # "제2조(정의)"
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)  # 현재 본문 (개정안 버퍼)
    original_body: Mapped[Optional[str]] = mapped_column(Text)  # 개정 모드 로드 원본
    change_type: Mapped[Optional[str]] = mapped_column(String(20))  # unchanged|add|modify|delete
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    project: Mapped["DraftingProject"] = relationship(back_populates="sections")
    stage: Mapped["DraftingStage"] = relationship(back_populates="sections")
    validations: Mapped[List["DraftingValidation"]] = relationship(
        back_populates="section", cascade="all, delete-orphan"
    )


class DraftingMessage(Base):
    """단계별 채팅 로그 (담당자 ↔ AI) (Prisma Message)"""
    __tablename__ = "drafting_messages"

    __table_args__ = (
        Index("idx_drafting_messages_stage_created", "stage_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    stage_id: Mapped[int] = mapped_column(
        ForeignKey("drafting_stages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user|ai|system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[Optional[dict]] = mapped_column(JSONB)  # 근거 위키 섹션 배열
    attachments: Mapped[Optional[dict]] = mapped_column(JSONB)  # 첨부 컨텍스트
    applied: Mapped[bool] = mapped_column(Boolean, default=False)  # 에디터 적용 여부
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    stage: Mapped["DraftingStage"] = relationship(back_populates="messages")


class DraftingValidation(Base):
    """검증 결과 — 인라인 힌트(Haiku) + 정밀 검증(Sonnet 매트릭스) (Prisma ValidationResult)"""
    __tablename__ = "drafting_validations"

    __table_args__ = (
        Index("idx_drafting_validations_section_verdict", "section_id", "verdict"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    section_id: Mapped[int] = mapped_column(
        ForeignKey("drafting_sections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    criterion_id: Mapped[str] = mapped_column(String(50), nullable=False)  # 위키 기준 ID (예: 3.3.1)
    source: Mapped[str] = mapped_column(String(20), nullable=False)  # ebansimsa|jungbigijun
    verdict: Mapped[str] = mapped_column(String(20), nullable=False)  # pass|fail|na|pending
    severity: Mapped[Optional[str]] = mapped_column(String(20))  # hint|violation
    reason: Mapped[Optional[str]] = mapped_column(Text)
    suggestion: Mapped[Optional[str]] = mapped_column(Text)  # AI 자동 수정 제안
    dismissed_reason: Mapped[Optional[str]] = mapped_column(Text)  # "이유 있는 예외" 사유
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    section: Mapped["DraftingSection"] = relationship(back_populates="validations")


class DraftingReference(Base):
    """타 지자체 참고 조례 (Prisma Reference)

    source=registered 인 경우 law-matcher 등록 조례를 참조(ordinance_id).
    """
    __tablename__ = "drafting_references"

    __table_args__ = (
        Index("idx_drafting_references_project", "project_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("drafting_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 등록 조례 참조(선택) — law-matcher 내부 조례를 참고로 끌어올 때
    ordinance_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("ordinances.id", ondelete="SET NULL"), nullable=True
    )
    source: Mapped[str] = mapped_column(String(20), nullable=False)  # file|opendata|paste|registered
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    municipality: Mapped[Optional[str]] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text, nullable=False)  # 조례 전문
    source_url: Mapped[Optional[str]] = mapped_column(String(500))
    included_in_context: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    project: Mapped["DraftingProject"] = relationship(back_populates="references")
    ordinance: Mapped[Optional["Ordinance"]] = relationship(viewonly=True)


class DraftingSnapshot(Base):
    """시간여행용 본문 스냅샷 — 채팅 로그와 별개 (Prisma Snapshot)"""
    __tablename__ = "drafting_snapshots"

    __table_args__ = (
        Index("idx_drafting_snapshots_stage_created", "stage_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    stage_id: Mapped[int] = mapped_column(
        ForeignKey("drafting_stages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    trigger_type: Mapped[str] = mapped_column(String(20), nullable=False)  # confirm|ai_apply|manual_save
    actor: Mapped[str] = mapped_column(String(20), nullable=False)  # user|ai
    label: Mapped[Optional[str]] = mapped_column(String(200))
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)  # 그 시점 조 단위 본문 스냅샷
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    stage: Mapped["DraftingStage"] = relationship(back_populates="snapshots")
