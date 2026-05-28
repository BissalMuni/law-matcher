"""조문 작성용 시스템 프롬프트 구성 + 근거(citations) 수집
(law-ebansimsa pipeline.draft.generator 포팅).

P1: 모든 AI 문장은 위키 근거를 추적 가능해야 하며, 근거 없는 내용은
NO_BASIS_TOKEN("[기준에 없음]")으로 명시한다.
P4: 참고 조례는 복제 금지를 AI에 강제한다.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

# 입안·정비 기준에 근거가 없는 내용을 표시하는 토큰 (지어내기 금지)
NO_BASIS_TOKEN = "[기준에 없음]"


class WikiGrounding(BaseModel):
    """AI 작성의 근거가 되는 위키 기준 섹션 1개"""
    criterion_id: str  # "ebansimsa/2.1.2"
    content: str = ""  # 위키 섹션 본문 (시스템 프롬프트에 주입)


class ReferenceContext(BaseModel):
    """타 지자체 참고 조례 1건 (참고만, 복제 금지 — P4)"""
    title: str
    content: str = ""
    municipality: str | None = None


class DraftRequest(BaseModel):
    """단계별 조문 작성 요청"""
    stage_key: str
    intent: str
    groundings: list[WikiGrounding] = Field(default_factory=list)
    references: list[ReferenceContext] = Field(default_factory=list)
    # 상위법령 컨텍스트 (law-matcher 통합 — 등록 조례의 상위법령 주입, Phase 3)
    parent_laws: list[str] = Field(default_factory=list)


def collect_citations(req: DraftRequest) -> list[str]:
    """요청의 근거 위키 기준 id 목록을 추출한다 (Message.citations 저장용 — P1)."""
    return [g.criterion_id for g in req.groundings]


def build_system_prompt(req: DraftRequest) -> str:
    """위키 근거 + 복제 금지 지시를 주입한 시스템 프롬프트를 만든다."""
    parts: list[str] = [
        "당신은 대한민국 지자체 조례 입안을 돕는 작성 보조자다.",
        f"현재 작성 단계: {req.stage_key}",
        f"담당자 의도: {req.intent}",
    ]

    # 상위법령 컨텍스트 (law-matcher 통합)
    if req.parent_laws:
        parts.append("\n## 상위법령 (이 조례가 근거·위임받는 법령)")
        for law in req.parent_laws:
            parts.append(f"- {law}")
        parts.append("위 상위법령의 위임 범위를 벗어나지 않도록 작성하라.")

    # P1 — 근거 위키 섹션 주입
    parts.append("\n## 입안·정비 기준 (근거)")
    if req.groundings:
        for g in req.groundings:
            parts.append(f"### {g.criterion_id}")
            if g.content:
                parts.append(g.content)
    else:
        parts.append("제공된 근거 기준이 없다.")

    # 근거 없는 내용은 반드시 표시, 지어내기 금지
    parts.append(
        f"\n위 기준에 근거가 없는 내용은 반드시 `{NO_BASIS_TOKEN}` 표기를 붙여라. "
        "근거를 지어내지 마라. 사용한 기준은 citation으로 추적 가능해야 한다."
    )

    # P4 — 참고 조례 복제 금지
    if req.references:
        parts.append("\n## 참고 조례 (참고만, 복제 금지)")
        for ref in req.references:
            label = ref.title
            if ref.municipality:
                label = f"{ref.municipality} · {ref.title}"
            parts.append(f"### {label}")
            if ref.content:
                parts.append(ref.content)
        parts.append(
            "\n위 참고 조례는 참고만 하고 그대로 복사하지 마라. "
            "문장을 복제하지 말고 현재 지자체 상황에 맞게 새로 작성하라."
        )

    return "\n".join(parts)
