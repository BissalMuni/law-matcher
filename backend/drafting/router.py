"""입안심사(drafting) 라우터 — /api/v1/drafting 아래 마운트.

Phase 2: 컴퓨트 엔드포인트 (parse/draft/validate/export/criteria) 포팅 완료.
Phase 3에서 등록 조례/상위법령 연동 + 영속화(프로젝트/단계/조문) 엔드포인트를 추가한다.
"""
from fastapi import APIRouter

from backend.core.config import settings
from backend.drafting.endpoints import (
    criteria,
    draft,
    export,
    parse,
    projects,
    sources,
    validate,
)

router = APIRouter()


@router.get("/health")
async def drafting_health() -> dict:
    """입안심사 모듈 상태 확인"""
    return {
        "module": "drafting",
        "enabled": settings.DRAFTING_ENABLED,
        "status": "ok",
    }


router.include_router(parse.router)
router.include_router(draft.router)
router.include_router(validate.router)
router.include_router(export.router)
router.include_router(criteria.router)
# Phase 3 — 등록 조례/상위법령 연동 + 영속화
router.include_router(sources.router)
router.include_router(projects.router)
