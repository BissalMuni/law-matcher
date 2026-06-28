"""law-matcher ↔ doc-ingest 연결 (조례 PDF 수집).

doc-ingest 라이브러리는 법령을 모른다. 조문(제N조) 같은 도메인 규칙은
여기서 Validator 로 구현해 extract(validators=[...]) 로 주입한다.
검증에 실패한 PDF 는 doc-ingest 의 miss_log 에 적재돼 픽스처 후보가 된다.
"""
from __future__ import annotations

import re

from doc_ingest import ExtractResult, ValidationReport, extract

# service.py 의 _ARTICLE_NO 와 동일한 조 번호 패턴
_ARTICLE_NO = re.compile(r"제(\d+)조")


class ArticleSequenceValidator:
    """제1조·제2조… 가 끊기지 않고 연속인지 검사하는 도메인 검증기.

    조문 번호는 같은 조 반복(여러 항·호) 또는 다음 조로의 증가만 허용한다.
    번호가 갑자기 건너뛰면 추출이 일부 누락됐을 가능성이 높다.
    """

    name = "article_sequence"

    def validate(self, result: ExtractResult) -> ValidationReport:
        nums: list[int] = [
            int(m.group(1)) for b in result.blocks for m in _ARTICLE_NO.finditer(b.text)
        ]
        issues: list[str] = []
        if not nums:
            issues.append("조문(제N조)을 하나도 찾지 못했습니다")
        for prev, cur in zip(nums, nums[1:]):
            if cur not in (prev, prev + 1):
                issues.append(f"조문 번호 불연속: 제{prev}조 → 제{cur}조")
        score = 1.0 if not issues else max(0.0, 1.0 - 0.2 * len(issues))
        return ValidationReport(ok=not issues, issues=issues, score=score)


def extract_ordinance_pdf(path: str) -> ExtractResult:
    """조례 PDF 를 추출하고 조문 연속성을 자동 검증한다."""
    return extract(path, validators=[ArticleSequenceValidator()])
