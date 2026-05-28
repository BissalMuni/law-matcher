"""심사 기준 로드 — registry + wiki 파일 읽기전용 서빙
(law-ebansimsa pipeline.review.criteria_loader 포팅).

데이터는 backend/drafting/data/ 에 이관된 criteria_registry.json + wiki/*.md 를 쓴다.
위키 기준은 문자열 id로만 참조한다(D1) — DB에 위키를 넣지 않는다.
registry id 규약: "<source>/<code>" (예: "ebansimsa/2.1.2").
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from backend.drafting.models import Criterion, CriterionScope

DATA_DIR = Path(__file__).parent / "data"
REGISTRY_PATH = DATA_DIR / "criteria_registry.json"
WIKI_DIR = DATA_DIR / "wiki"


def _split_id(registry_id: str) -> tuple[str, str]:
    """'ebansimsa/2.1.2' → ('ebansimsa', '2.1.2')"""
    source, _, code = registry_id.partition("/")
    return source, code


def _wiki_file(source: str, wiki_path: str) -> Path:
    """registry의 wiki_path(예: 'output\\ebansimsa\\wiki\\x.md')를
    이관된 data/wiki/<source>/<basename> 로 해석한다."""
    basename = Path(wiki_path.replace("\\", "/")).name
    return WIKI_DIR / source / basename


def _strip_frontmatter(raw: str) -> str:
    if raw.startswith("---"):
        end = raw.find("---", 3)
        if end != -1:
            return raw[end + 3:].strip()
    return raw


@lru_cache(maxsize=1)
def _registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def load_criteria(load_content: bool = True) -> list[Criterion]:
    """레지스트리에서 활성 기준을 로드한다."""
    data = _registry()
    criteria: list[Criterion] = []
    for entry in data["criteria"]:
        if not entry.get("enabled", True):
            continue
        source, _ = _split_id(entry["id"])
        criterion = Criterion(
            id=entry["id"],
            title=entry["title"],
            scope=CriterionScope(entry["scope"]),
            wiki_path=entry["wiki_path"],
        )
        if load_content:
            wf = _wiki_file(source, entry["wiki_path"])
            if wf.exists():
                criterion.content = _strip_frontmatter(wf.read_text(encoding="utf-8"))
        criteria.append(criterion)
    return criteria


def catalog() -> list[dict]:
    """검증/매핑 UI용 기준 카탈로그 (content 제외, 메타만).

    반환 각 항목: {criterion_id, source, title} — criterion_id는 source 없는 코드.
    """
    items: list[dict] = []
    for c in load_criteria(load_content=False):
        source, code = _split_id(c.id)
        items.append({"criterion_id": code, "source": source, "title": c.title})
    return items


def get_content(registry_id: str) -> str | None:
    """registry id('source/code')로 위키 전문을 반환한다 (draft groundings용)."""
    data = _registry()
    for entry in data["criteria"]:
        if entry["id"] != registry_id:
            continue
        source, _ = _split_id(registry_id)
        wf = _wiki_file(source, entry["wiki_path"])
        if wf.exists():
            return _strip_frontmatter(wf.read_text(encoding="utf-8"))
        return None
    return None
