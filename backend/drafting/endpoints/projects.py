"""입안심사 프로젝트/단계/조문/메시지/검증/스냅샷 영속화 엔드포인트 (Phase 3)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db
from backend.drafting.api_schemas import (
    MessageCreateRequest,
    MessageOut,
    ProjectCreateRequest,
    ProjectDetailOut,
    ProjectOut,
    SectionOut,
    SectionUpsertRequest,
    SnapshotCreateRequest,
    StageOut,
    StageStatusUpdate,
    ValidationOut,
    ValidationSaveRequest,
)
from backend.drafting.service import DraftingService

router = APIRouter()


# ---------- 프로젝트 ----------

@router.post("/projects", response_model=ProjectOut)
async def create_project(
    body: ProjectCreateRequest, db: AsyncSession = Depends(get_db)
) -> ProjectOut:
    service = DraftingService(db)
    project = await service.create_project(
        kind=body.kind,
        title=body.title,
        municipality=body.municipality,
        ordinance_id=body.ordinance_id,
        source_url=body.source_url,
    )
    return ProjectOut.model_validate(project)


@router.get("/projects", response_model=list[ProjectOut])
async def list_projects(db: AsyncSession = Depends(get_db)) -> list[ProjectOut]:
    service = DraftingService(db)
    return [ProjectOut.model_validate(p) for p in await service.list_projects()]


@router.get("/projects/{project_id}", response_model=ProjectDetailOut)
async def get_project(project_id: int, db: AsyncSession = Depends(get_db)) -> ProjectDetailOut:
    service = DraftingService(db)
    project = await service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다.")
    parent_laws = (
        await service.get_parent_laws(project.ordinance_id) if project.ordinance_id else []
    )
    detail = ProjectDetailOut.model_validate(project)
    detail.stages = sorted(
        [StageOut.model_validate(s) for s in project.stages], key=lambda s: s.sort_order
    )
    detail.sections = sorted(
        [SectionOut.model_validate(s) for s in project.sections], key=lambda s: s.sort_order
    )
    detail.parent_laws = parent_laws
    return detail


@router.delete("/projects/{project_id}")
async def delete_project(project_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    service = DraftingService(db)
    ok = await service.delete_project(project_id)
    if not ok:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다.")
    return {"deleted": True}


# ---------- 단계 ----------

@router.get("/projects/{project_id}/stages", response_model=list[StageOut])
async def list_stages(project_id: int, db: AsyncSession = Depends(get_db)) -> list[StageOut]:
    service = DraftingService(db)
    return [StageOut.model_validate(s) for s in await service.list_stages(project_id)]


@router.patch("/stages/{stage_id}", response_model=StageOut)
async def update_stage(
    stage_id: int, body: StageStatusUpdate, db: AsyncSession = Depends(get_db)
) -> StageOut:
    service = DraftingService(db)
    stage = await service.update_stage_status(stage_id, body.status, body.stale_reason)
    if not stage:
        raise HTTPException(status_code=404, detail="단계를 찾을 수 없습니다.")
    return StageOut.model_validate(stage)


# ---------- 조문 ----------

@router.get("/projects/{project_id}/sections", response_model=list[SectionOut])
async def list_sections(project_id: int, db: AsyncSession = Depends(get_db)) -> list[SectionOut]:
    service = DraftingService(db)
    return [SectionOut.model_validate(s) for s in await service.list_sections(project_id)]


@router.post("/sections", response_model=SectionOut)
async def upsert_section(
    body: SectionUpsertRequest, db: AsyncSession = Depends(get_db)
) -> SectionOut:
    service = DraftingService(db)
    section = await service.upsert_section(body.model_dump())
    return SectionOut.model_validate(section)


@router.delete("/sections/{section_id}")
async def delete_section(section_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    service = DraftingService(db)
    ok = await service.delete_section(section_id)
    if not ok:
        raise HTTPException(status_code=404, detail="조문을 찾을 수 없습니다.")
    return {"deleted": True}


# ---------- 메시지 ----------

@router.get("/stages/{stage_id}/messages", response_model=list[MessageOut])
async def list_messages(stage_id: int, db: AsyncSession = Depends(get_db)) -> list[MessageOut]:
    service = DraftingService(db)
    return [MessageOut.model_validate(m) for m in await service.list_messages(stage_id)]


@router.post("/stages/{stage_id}/messages", response_model=MessageOut)
async def add_message(
    stage_id: int, body: MessageCreateRequest, db: AsyncSession = Depends(get_db)
) -> MessageOut:
    service = DraftingService(db)
    data = body.model_dump()
    data["stage_id"] = stage_id
    msg = await service.add_message(data)
    return MessageOut.model_validate(msg)


# ---------- 검증 ----------

@router.get("/sections/{section_id}/validations", response_model=list[ValidationOut])
async def list_validations(
    section_id: int, db: AsyncSession = Depends(get_db)
) -> list[ValidationOut]:
    service = DraftingService(db)
    return [ValidationOut.model_validate(v) for v in await service.list_validations(section_id)]


@router.post("/sections/{section_id}/validations")
async def save_validations(
    section_id: int, body: ValidationSaveRequest, db: AsyncSession = Depends(get_db)
) -> dict:
    service = DraftingService(db)
    count = await service.save_validations(
        section_id, [r.model_dump() for r in body.results], replace=body.replace
    )
    return {"saved": count}


# ---------- 스냅샷 ----------

@router.post("/stages/{stage_id}/snapshots")
async def create_snapshot(
    stage_id: int, body: SnapshotCreateRequest, db: AsyncSession = Depends(get_db)
) -> dict:
    service = DraftingService(db)
    data = body.model_dump()
    data["stage_id"] = stage_id
    snap = await service.create_snapshot(data)
    return {"id": snap.id, "created_at": snap.created_at.isoformat()}
