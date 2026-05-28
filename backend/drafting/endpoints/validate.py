"""검증 매트릭스 — 스크립트가 셀(조문×기준)을 강제 생성하고 LLM은 1회 1셀만 판단한다.

POST /drafting/validate/precise — 단계 확정 시 정밀 검증, 전 셀 충족 검증
POST /drafting/validate/inline  — 작성 중 가벼운 힌트 (fast 모델)
POST /drafting/validate/full    — Stage 7 전체 검토 (2단계)
POST /drafting/validate/map-criteria — 조문에 적용되는 기준 AI 매핑
위키 기준은 문자열(criterion_id)로만 참조한다 (D1).
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.drafting.llm import DraftingLLM
from backend.drafting.schemas import ArticleInput, CriterionCell, ValidationCellResult

router = APIRouter()

CellJudge = Callable[[ArticleInput, CriterionCell, str], Awaitable[ValidationCellResult]]
RelevanceFilter = Callable[[ArticleInput, CriterionCell], bool]
CriteriaMapper = Callable[[ArticleInput, list[CriterionCell]], Awaitable[list[str]]]

_FILLED_VERDICTS = {"pass", "fail", "na"}


def get_relevance_filter() -> RelevanceFilter:
    """1단계 관련성 필터 — 기본은 전부 관련(상세 판단). 테스트는 오버라이드한다."""

    def relevant(article: ArticleInput, criterion: CriterionCell) -> bool:
        return True

    return relevant


def get_cell_judge() -> CellJudge:
    """실제 LLM 셀 판단기 — 1조문×1기준만 받는다. 테스트는 가짜로 오버라이드한다."""
    client = DraftingLLM()

    async def judge(
        article: ArticleInput, criterion: CriterionCell, severity: str
    ) -> ValidationCellResult:
        system = (
            "당신은 조례 심사자다. 단 하나의 조문을 단 하나의 기준으로만 판단하라.\n"
            f"기준: {criterion.source}/{criterion.criterion_id} ({criterion.title or ''})\n\n"
            "반드시 아래 JSON 형식으로만 답하라(다른 텍스트 금지):\n"
            '{"verdict": "pass|fail|na", "reason": "판단 근거 1~2문장", '
            '"suggestion": "fail 일 때 수정 제안, 아니면 빈 문자열"}\n'
            "- pass: 기준 충족 / fail: 위반 / na: 이 조문에 무관한 기준"
        )
        user = f"[{article.article_id} {article.title}]\n{article.text}"
        result = await client.call(system, user, use_fast=(severity == "hint"))
        verdict = result.get("verdict", "pending") if isinstance(result, dict) else "pending"
        if verdict not in {"pass", "fail", "na", "pending"}:
            verdict = "pending"
        return ValidationCellResult(
            article_id=article.article_id,
            criterion_id=criterion.criterion_id,
            source=criterion.source,
            verdict=verdict,
            severity=severity,  # type: ignore[arg-type]
            reason=result.get("reason") if isinstance(result, dict) else None,
            suggestion=result.get("suggestion") if isinstance(result, dict) else None,
        )

    return judge


def get_criteria_mapper() -> CriteriaMapper:
    """조문에 적용되는 기준을 카탈로그에서 고르는 AI 매퍼. 테스트는 오버라이드한다."""
    client = DraftingLLM()

    async def mapper(article: ArticleInput, criteria: list[CriterionCell]) -> list[str]:
        catalog = "\n".join(
            f"- {c.source}/{c.criterion_id}: {c.title or ''}" for c in criteria
        )
        system = (
            "당신은 조례 심사자다. 주어진 조문에 '실제로 적용되는' 입안심사·정비 기준만 고른다.\n"
            "조문의 성격(정의·목적·벌칙·위임 등)과 직접 관련된 기준만 선택하고, "
            "무관한 기준은 절대 넣지 마라.\n"
            "반드시 아래 JSON 형식으로만 답하라(다른 텍스트 금지):\n"
            '{"criterion_ids": ["<source>/<id>", ...]}\n'
            "id 는 카탈로그의 'source/id' 표기를 그대로 쓴다."
        )
        user = (
            f"[조문] {article.article_id} {article.title}\n{article.text}\n\n"
            f"[기준 카탈로그]\n{catalog}"
        )
        result = await client.call(system, user, max_tokens=512)
        ids = result.get("criterion_ids", []) if isinstance(result, dict) else []
        return [str(i) for i in ids] if isinstance(ids, list) else []

    return mapper


class MapCriteriaRequest(BaseModel):
    article: ArticleInput
    criteria: list[CriterionCell]


class MapCriteriaResponse(BaseModel):
    criteria: list[CriterionCell]


@router.post("/validate/map-criteria", response_model=MapCriteriaResponse)
async def map_criteria(
    body: MapCriteriaRequest,
    mapper: CriteriaMapper = Depends(get_criteria_mapper),
) -> MapCriteriaResponse:
    """조문에 적용되는 기준을 카탈로그에서 추려 반환한다 (AI 자동 매핑)."""
    selected = set(await mapper(body.article, body.criteria))
    chosen = [c for c in body.criteria if f"{c.source}/{c.criterion_id}" in selected]
    return MapCriteriaResponse(criteria=chosen)


class PreciseRequest(BaseModel):
    articles: list[ArticleInput]
    criteria: list[CriterionCell]


class PreciseResponse(BaseModel):
    results: list[ValidationCellResult]
    total_cells: int
    filled_cells: int
    complete: bool


@router.post("/validate/precise", response_model=PreciseResponse)
async def validate_precise(
    body: PreciseRequest, judge: CellJudge = Depends(get_cell_judge)
) -> PreciseResponse:
    # 모든 (조문 × 기준) 셀을 셀 단위로 판단 (누락 0건)
    results: list[ValidationCellResult] = []
    for article in body.articles:
        for criterion in body.criteria:
            results.append(await judge(article, criterion, "violation"))

    total = len(body.articles) * len(body.criteria)
    filled = sum(1 for r in results if r.verdict in _FILLED_VERDICTS)
    return PreciseResponse(
        results=results,
        total_cells=total,
        filled_cells=filled,
        complete=(total > 0 and filled == total),
    )


class InlineRequest(BaseModel):
    article: ArticleInput
    criteria: list[CriterionCell] = Field(default_factory=list)


class InlineResponse(BaseModel):
    hints: list[ValidationCellResult]


@router.post("/validate/inline", response_model=InlineResponse)
async def validate_inline(
    body: InlineRequest, judge: CellJudge = Depends(get_cell_judge)
) -> InlineResponse:
    criterion = body.criteria[0] if body.criteria else CriterionCell(
        criterion_id="relevance", source="ebansimsa", title="관련성"
    )
    hint = await judge(body.article, criterion, "hint")
    return InlineResponse(hints=[hint])


class FullRequest(BaseModel):
    articles: list[ArticleInput]
    criteria: list[CriterionCell]


class FullResponse(BaseModel):
    results: list[ValidationCellResult]
    total_cells: int
    filled_cells: int
    complete: bool


@router.post("/validate/full", response_model=FullResponse)
async def validate_full(
    body: FullRequest,
    judge: CellJudge = Depends(get_cell_judge),
    is_relevant: RelevanceFilter = Depends(get_relevance_filter),
) -> FullResponse:
    """Stage 7 전체 검토 — 2단계(관련성 필터 → 셀 판단). 비관련 셀은 na로 채운다."""
    results: list[ValidationCellResult] = []
    for article in body.articles:
        for criterion in body.criteria:
            if is_relevant(article, criterion):
                results.append(await judge(article, criterion, "violation"))
            else:
                results.append(
                    ValidationCellResult(
                        article_id=article.article_id,
                        criterion_id=criterion.criterion_id,
                        source=criterion.source,
                        verdict="na",
                        severity="violation",
                        reason="해당 조문에 관련 없는 기준",
                    )
                )

    total = len(body.articles) * len(body.criteria)
    filled = sum(1 for r in results if r.verdict in _FILLED_VERDICTS)
    return FullResponse(
        results=results,
        total_cells=total,
        filled_cells=filled,
        complete=(total > 0 and filled == total),
    )
