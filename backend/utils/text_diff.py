"""
Text diff utilities for law comparison
"""
from typing import List, Dict, Any
from difflib import SequenceMatcher, unified_diff


def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate similarity ratio between two texts"""
    return SequenceMatcher(None, text1, text2).ratio()


def get_unified_diff(old_text: str, new_text: str, context: int = 3) -> List[str]:
    """Get unified diff between two texts"""
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)

    diff = unified_diff(
        old_lines,
        new_lines,
        fromfile="old",
        tofile="new",
        n=context,
    )
    return list(diff)


def compare_articles(
    old_articles: Dict[str, str],
    new_articles: Dict[str, str],
) -> Dict[str, List]:
    """
    Compare two sets of articles.

    Args:
        old_articles: Dict of article_no -> content
        new_articles: Dict of article_no -> content

    Returns:
        Dict with 'added', 'modified', 'deleted' keys
    """
    result = {
        "added": [],
        "modified": [],
        "deleted": [],
    }

    # Find added and modified
    for art_no, content in new_articles.items():
        if art_no not in old_articles:
            result["added"].append(art_no)
        elif content != old_articles[art_no]:
            result["modified"].append({
                "article_no": art_no,
                "old_content": old_articles[art_no],
                "new_content": content,
                "similarity": calculate_similarity(old_articles[art_no], content),
            })

    # Find deleted
    for art_no in old_articles:
        if art_no not in new_articles:
            result["deleted"].append(art_no)

    return result


def extract_citations(text: str) -> List[str]:
    """
    Extract law citations from text.

    Examples:
        "법 제5조" -> ["법 제5조"]
        "시행령 제10조제1항" -> ["시행령 제10조제1항"]
    """
    import re

    pattern = r'(?:법|시행령|시행규칙)\s*제\d+조(?:의\d+)?(?:제\d+항)?(?:제\d+호)?'
    return re.findall(pattern, text)
