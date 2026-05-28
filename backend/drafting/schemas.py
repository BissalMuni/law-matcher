"""입안심사 컴퓨트 엔드포인트 Pydantic 스키마 (law-ebansimsa api.schemas 포팅).

Literal 허용값은 backend/models/drafting.py 의 String enum 주석과 1:1 매칭한다.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

ProjectKind = Literal["enact", "amend_partial", "amend_full"]
StageKey = Literal[
    "meta", "purpose", "definition", "scope",
    "main", "supplementary", "review", "finalize",
]
Verdict = Literal["pass", "fail", "na", "pending"]
CriterionSource = Literal["ebansimsa", "jungbigijun"]
Severity = Literal["hint", "violation"]
ReferenceSource = Literal["file", "opendata", "paste", "registered"]


class ArticleInput(BaseModel):
    """검증 입력 조문 1건 (조 단위)"""
    article_id: str  # "제1조"
    title: str       # "목적"
    text: str        # 조문 전문


class CriterionCell(BaseModel):
    """검증 매트릭스의 기준 1개 (위키 기준은 문자열 참조 — D1)"""
    criterion_id: str  # "2.1.2" (source 없는 코드)
    source: CriterionSource
    title: str | None = None


class ValidationCellResult(BaseModel):
    """매트릭스 한 셀(1조문×1기준)의 판단 결과"""
    article_id: str
    criterion_id: str
    source: CriterionSource
    verdict: Verdict
    severity: Severity
    reason: str | None = None
    suggestion: str | None = None
    dismissed_reason: str | None = None
