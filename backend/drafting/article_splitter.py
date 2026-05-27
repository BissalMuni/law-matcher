"""조례안을 개별 조문으로 분리하는 모듈 (law-ebansimsa pipeline.review.article_splitter 포팅)."""
from __future__ import annotations

import re

from backend.drafting.models import Article, DOCUMENT_ID

# 조문 패턴: 제1조, 제2조의2, 제10조 등
_ARTICLE_PATTERN = re.compile(
    r'^(제\d+조(?:의\d+)?)\s*(?:\(([^)]*)\))?\s*',
    re.MULTILINE,
)

# 부칙 패턴
_ADDENDUM_PATTERN = re.compile(r'^\s*부\s*칙', re.MULTILINE)

# 별표 패턴
_APPENDIX_PATTERN = re.compile(r'^\s*\[별표', re.MULTILINE)


def split_ordinance(text: str) -> list[Article]:
    """조례안 텍스트를 개별 조문으로 분리한다.

    반환값에는 항상 __DOCUMENT__ (전체 텍스트)가 포함된다.
    """
    articles: list[Article] = []

    # __DOCUMENT__: 전체 텍스트 (document_level 심사용)
    articles.append(Article(
        id=DOCUMENT_ID,
        title="전체 문서",
        text=text.strip(),
        index=0,
    ))

    matches = list(_ARTICLE_PATTERN.finditer(text))
    if not matches:
        return articles

    boundaries = [(m.start(), m) for m in matches]
    addendum = _ADDENDUM_PATTERN.search(text)
    appendix = _APPENDIX_PATTERN.search(text)

    for idx, (_, match) in enumerate(boundaries):
        article_id = match.group(1)            # 제1조
        article_title = match.group(2) or ""   # (목적)

        start = match.start()
        if idx + 1 < len(boundaries):
            end = boundaries[idx + 1][0]
        elif addendum and addendum.start() > start:
            end = addendum.start()
        elif appendix and appendix.start() > start:
            end = appendix.start()
        else:
            end = len(text)

        article_text = text[start:end].strip()

        articles.append(Article(
            id=article_id,
            title=article_title,
            text=article_text,
            index=idx + 1,
        ))

    # 부칙이 있으면 별도 조문으로 추가
    if addendum:
        addendum_start = addendum.start()
        addendum_end = (
            appendix.start()
            if appendix and appendix.start() > addendum_start
            else len(text)
        )
        addendum_text = text[addendum_start:addendum_end].strip()
        if addendum_text:
            articles.append(Article(
                id="부칙",
                title="",
                text=addendum_text,
                index=len(articles),
            ))

    return articles
