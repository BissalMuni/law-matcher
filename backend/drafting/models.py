"""입안심사 컴퓨트 데이터 모델 (law-ebansimsa pipeline.review.models 포팅).

DB ORM 모델이 아니라 파이프라인 내부 dataclass다. 영속화 모델은
backend/models/drafting.py 의 SQLAlchemy 모델을 쓴다.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CriterionScope(str, Enum):
    PER_ARTICLE = "per_article"
    DOCUMENT_LEVEL = "document_level"


DOCUMENT_ID = "__DOCUMENT__"


@dataclass
class Article:
    """조례안의 개별 조문"""
    id: str          # "제1조", "제2조", ... 또는 "__DOCUMENT__"
    title: str       # "(목적)", "(정의)" 등
    text: str        # 조문 전문
    index: int       # 0부터 시작하는 순서


@dataclass
class Criterion:
    """심사 기준 (wiki 페이지 1개 = 기준 1개)"""
    id: str               # "ebansimsa/2.1.2"
    title: str            # "목적규정"
    scope: CriterionScope
    wiki_path: str        # wiki 파일 상대 경로 (registry 기준)
    content: str = ""     # 런타임에 로드되는 wiki 전문
    enabled: bool = True
