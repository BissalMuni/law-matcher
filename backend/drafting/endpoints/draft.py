"""POST /drafting/draft/generate (SSE) — 단계별 조문 작성 스트림 + citations.

P1(근거 추적)·P4(복제 금지)는 generator의 시스템 프롬프트가 강제한다.
근거(wiki) 내용이 비어 있으면 이관된 위키에서 자동 backfill 한다 (law-matcher 통합).
"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.drafting import criteria as criteria_mod
from backend.drafting.generator import (
    DraftRequest,
    ReferenceContext,
    WikiGrounding,
    build_system_prompt,
    collect_citations,
)
from backend.drafting.llm import stream_text

router = APIRouter()


class WikiRefInput(BaseModel):
    criterion_id: str  # "ebansimsa/2.1.2" (full registry id)
    content: str = ""


class DraftGenerateRequest(BaseModel):
    stage_key: str
    intent: str
    wiki_refs: list[WikiRefInput] = Field(default_factory=list)
    references: list[ReferenceContext] = Field(default_factory=list)
    parent_laws: list[str] = Field(default_factory=list)

    def to_draft_request(self) -> DraftRequest:
        groundings = []
        for r in self.wiki_refs:
            content = r.content or (criteria_mod.get_content(r.criterion_id) or "")
            groundings.append(WikiGrounding(criterion_id=r.criterion_id, content=content))
        return DraftRequest(
            stage_key=self.stage_key,
            intent=self.intent,
            groundings=groundings,
            references=self.references,
            parent_laws=self.parent_laws,
        )


# LLM 스트리머 — 테스트는 이 의존성을 가짜로 오버라이드한다.
def get_streamer():
    return stream_text


def _sse(data: str) -> str:
    return f"data: {data}\n\n"


@router.post("/draft/generate")
async def draft_generate(
    body: DraftGenerateRequest,
    streamer=Depends(get_streamer),
) -> StreamingResponse:
    req = body.to_draft_request()
    system = build_system_prompt(req)
    citations = collect_citations(req)

    async def event_stream() -> AsyncIterator[str]:
        # 먼저 근거(citations)를 흘려 web이 Message.citations로 저장하게 한다 (P1)
        yield _sse(json.dumps({"type": "citations", "citations": citations}, ensure_ascii=False))
        async for chunk in streamer(system, req.intent):
            yield _sse(json.dumps({"type": "delta", "text": chunk}, ensure_ascii=False))
        yield _sse("[DONE]")

    return StreamingResponse(event_stream(), media_type="text/event-stream")
