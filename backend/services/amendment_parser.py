"""
Amendment content parser for revision detection.
"""
import re
from typing import Any, Dict, List, Sequence

ARTICLE_PATTERN = re.compile(r"제(\d+조(?:의\d+)?)")


def _normalize_article_no(value: str) -> str:
    if not value:
        return ""
    matched = ARTICLE_PATTERN.search(str(value))
    if not matched:
        return ""
    return f"제{matched.group(1)}"


def _article_sort_key(article_no: str) -> tuple:
    matched = re.match(r"^제(\d+)조(?:의(\d+))?$", article_no)
    if not matched:
        return (10**9, 10**9, article_no)
    main_no = int(matched.group(1))
    sub_no = int(matched.group(2)) if matched.group(2) else 0
    return (main_no, sub_no, article_no)


def parse_amendment_articles(text: str) -> List[str]:
    """
    개정문에서 조문번호를 추출하여 중복 제거 + 정렬 반환.
    패턴: 제(\d+조(?:의\d+)?)
    """
    if not text:
        return []

    extracted = [f"제{m}" for m in ARTICLE_PATTERN.findall(text)]
    unique = sorted(set(extracted), key=_article_sort_key)
    return unique


def match_articles_to_ordinance(
    articles: Sequence[str],
    mapped: Sequence[str],
) -> Dict[str, Any]:
    """
    추출 조문과 조례 매핑 조문을 대조한다.
    - 매핑된 추출 조문: 검토 필요
    - 비매핑 추출 조문: 참고(매핑 검토)
    """
    normalized_extracted = sorted(
        {item for item in (_normalize_article_no(a) for a in articles) if item},
        key=_article_sort_key,
    )
    normalized_mapped = sorted(
        {item for item in (_normalize_article_no(m) for m in mapped) if item},
        key=_article_sort_key,
    )

    mapped_set = set(normalized_mapped)
    extracted_set = set(normalized_extracted)

    review_required = sorted(extracted_set & mapped_set, key=_article_sort_key)
    reference_only = sorted(extracted_set - mapped_set, key=_article_sort_key)
    mapped_not_mentioned = sorted(mapped_set - extracted_set, key=_article_sort_key)

    return {
        "extracted_articles": normalized_extracted,
        "mapped_articles": normalized_mapped,
        "review_required_articles": review_required,
        "reference_articles": reference_only,
        "mapped_not_mentioned": mapped_not_mentioned,
        "needs_revision": len(review_required) > 0,
    }
