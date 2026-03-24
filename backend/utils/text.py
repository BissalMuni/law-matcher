"""
텍스트 정규화 유틸리티

법제처 API 기준 문자 정규화 함수를 제공합니다.
"""
import unicodedata
from typing import Optional

# 법제처 기준 중간점: ㆍ (U+318D, HANGUL LETTER ARAEYA)
CANONICAL_MIDDLE_DOT = "ㆍ"  # U+318D

# 중간점 유니코드 변형 목록
_MIDDLE_DOT_VARIANTS = (
    "\u00B7",  # · MIDDLE DOT
    "\u119E",  # ᆞ HANGUL JUNGSEONG ARAEA
    "\u30FB",  # ・ KATAKANA MIDDLE DOT
    "\u2022",  # • BULLET
    "\uFF65",  # ･ HALFWIDTH KATAKANA MIDDLE DOT
)


def normalize_middle_dot(text: str) -> str:
    """
    중간점 유니코드 변형을 법제처 기준 ㆍ(U+318D)로 통일합니다.

    법제처 API가 반환하는 법령명의 중간점은 ㆍ(U+318D)입니다.
    프론트엔드나 엑셀 등 외부 입력에서 다른 코드포인트의 중간점이
    들어올 수 있으므로, 저장 전에 이 함수로 정규화합니다.
    """
    for dot in _MIDDLE_DOT_VARIANTS:
        text = text.replace(dot, CANONICAL_MIDDLE_DOT)
    return text


def normalize_name(name: Optional[str]) -> str:
    """
    법령명/조례명 저장용 정규화.

    - NFC 유니코드 정규화
    - 중간점 → ㆍ(U+318D) 통일
    - 앞뒤 공백 제거
    """
    if not name:
        return ""
    text = unicodedata.normalize("NFC", str(name))
    text = normalize_middle_dot(text)
    return text.strip()


def normalize_name_for_compare(name: Optional[str]) -> str:
    """
    법령명 비교용 정규화 (검색/매칭 시 사용).

    - normalize_name + 모든 공백 제거
    """
    return "".join(normalize_name(name).split())
