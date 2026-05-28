"""GET /drafting/criteria — 기준 카탈로그 + 위키 본문 읽기전용 서빙."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from backend.drafting import criteria as criteria_mod

router = APIRouter()


@router.get("/criteria")
def list_criteria() -> dict:
    """검증/매핑 UI용 기준 카탈로그 (criterion_id, source, title)."""
    return {"criteria": criteria_mod.catalog()}


@router.get("/criteria/content")
def criterion_content(id: str = Query(..., description="registry id, 예: ebansimsa/2.1.2")) -> dict:
    """위키 기준 전문을 반환한다 (draft groundings·근거 표시용)."""
    content = criteria_mod.get_content(id)
    if content is None:
        raise HTTPException(status_code=404, detail=f"기준을 찾을 수 없습니다: {id}")
    return {"id": id, "content": content}
