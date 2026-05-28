"""기존 조례 원문을 조(條) 단위로 파싱한다 (law-ebansimsa pipeline.search.parser 포팅).

개정 모드 로드용. 조 단위로 분리하고 항·호는 본문 마크업으로 둔다.
"""
from __future__ import annotations

import re

from backend.drafting.article_splitter import split_ordinance
from backend.drafting.models import DOCUMENT_ID

_ARTICLE_NO = re.compile(r"제(\d+)조")


class ParsedArticle:
    """조 단위 파싱 결과 (drafting_sections 로 저장됨)"""

    def __init__(self, article_no: int, title: str, article_label: str, body: str, order: int):
        self.article_no = article_no
        self.title = title
        self.article_label = article_label
        self.body = body
        self.order = order

    def to_dict(self) -> dict:
        return {
            "article_no": self.article_no,
            "title": self.title,
            "article_label": self.article_label,
            "body": self.body,
            "order": self.order,
        }


def parse_ordinance(content: str) -> list[ParsedArticle]:
    """조례 원문을 실제 조문(__DOCUMENT__·부칙 제외)만 조 단위로 분리한다."""
    parsed: list[ParsedArticle] = []
    order = 0
    for article in split_ordinance(content):
        if article.id == DOCUMENT_ID or article.id == "부칙":
            continue
        m = _ARTICLE_NO.search(article.id)
        if not m:
            continue
        article_no = int(m.group(1))
        title = article.title  # "(목적)"에서 괄호 제거된 "목적"
        label = f"{article.id}({title})" if title else article.id
        parsed.append(
            ParsedArticle(
                article_no=article_no,
                title=title,
                article_label=label,
                body=article.text,
                order=order,
            )
        )
        order += 1
    return parsed
