"""입안심사 영속화 엔드포인트 요청/응답 스키마 (Phase 3)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------- 요청 ----------

class ProjectCreateRequest(BaseModel):
    kind: str  # enact | amend_partial | amend_full
    title: str
    municipality: str
    ordinance_id: Optional[int] = None  # 등록 조례에서 시작 (개정)
    source_url: Optional[str] = None


class StageStatusUpdate(BaseModel):
    status: str
    stale_reason: Optional[str] = None


class SectionUpsertRequest(BaseModel):
    id: Optional[int] = None
    project_id: int
    stage_id: int
    article_no: int = 0
    article_label: Optional[str] = None
    title: str = ""
    body: str = ""
    original_body: Optional[str] = None
    change_type: Optional[str] = None
    sort_order: int = 0


class MessageCreateRequest(BaseModel):
    role: str  # user | ai | system
    content: str
    citations: Optional[list[str]] = None
    attachments: Optional[Any] = None
    applied: bool = False


class ValidationItem(BaseModel):
    criterion_id: str
    source: str
    verdict: str
    severity: Optional[str] = None
    reason: Optional[str] = None
    suggestion: Optional[str] = None
    dismissed_reason: Optional[str] = None


class ValidationSaveRequest(BaseModel):
    results: list[ValidationItem]
    replace: bool = True


class SnapshotCreateRequest(BaseModel):
    trigger_type: str  # confirm | ai_apply | manual_save
    actor: str         # user | ai
    label: Optional[str] = None
    content: Any


# ---------- 응답 ----------

class StageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    key: str
    label: str
    sort_order: int
    required: bool
    status: str
    stale_reason: Optional[str] = None
    wiki_ref: Optional[str] = None
    parent_id: Optional[int] = None
    confirmed_at: Optional[datetime] = None


class SectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    stage_id: int
    article_no: int
    article_label: Optional[str] = None
    title: str
    body: str
    original_body: Optional[str] = None
    change_type: Optional[str] = None
    sort_order: int


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    stage_id: int
    role: str
    content: str
    citations: Optional[Any] = None
    attachments: Optional[Any] = None
    applied: bool
    created_at: datetime


class ValidationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    section_id: int
    criterion_id: str
    source: str
    verdict: str
    severity: Optional[str] = None
    reason: Optional[str] = None
    suggestion: Optional[str] = None
    dismissed_reason: Optional[str] = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    kind: str
    title: str
    municipality: str
    ordinance_id: Optional[int] = None
    source_url: Optional[str] = None
    status: str
    progress: int
    created_at: datetime
    updated_at: datetime


class ProjectDetailOut(ProjectOut):
    stages: list[StageOut] = Field(default_factory=list)
    sections: list[SectionOut] = Field(default_factory=list)
    parent_laws: list[dict] = Field(default_factory=list)
