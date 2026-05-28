"""POST /drafting/parse/ordinance — 기존 조례 원문을 조 단위로 파싱."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from backend.drafting.parser import parse_ordinance

router = APIRouter()


class ParseRequest(BaseModel):
    content: str


@router.post("/parse/ordinance")
def parse_ordinance_endpoint(body: ParseRequest) -> dict:
    articles = [a.to_dict() for a in parse_ordinance(body.content)]
    return {"articles": articles}
