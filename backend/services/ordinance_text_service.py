"""조례 전문(본문) 캐시 헬퍼.

DB 캐시(ordinance_texts) 확인 → 없으면 법제처 API fetch → 저장하는 공용 로직.
입안심사 시드(backend.drafting.service)와 LLM 분석(backend.services.llm_analysis_service)이
함께 사용한다. 이 함수는 flush 까지만 수행하며, commit 은 호출 측에서 한다
(get_db 가 자동 커밋하지 않는 패턴과 일치).
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.ordinance import Ordinance
from backend.models.ordinance_text import OrdinanceText

logger = logging.getLogger(__name__)


def build_full_text(articles) -> str:
    """조문 리스트를 텍스트로 직렬화한다 (조문 사이 빈 줄 구분)."""
    lines: list[str] = []
    for art in articles:
        header = art.article_no
        if art.article_title:
            header += f"({art.article_title})"
        lines.append(header)
        if art.article_content:
            lines.append(art.article_content)
        lines.append("")  # 빈 줄 구분
    return "\n".join(lines).strip()


async def get_or_fetch_ordinance_text(
    db: AsyncSession,
    ordinance: Ordinance,
    api_key: str,
) -> Optional[OrdinanceText]:
    """조례 전문 조회 — DB 캐시 확인 → 없으면 법제처 API fetch → ordinance_texts 저장.

    반환: 조문이 채워진 OrdinanceText 행.
    serial_no 가 없거나 fetch 실패 시 기존 캐시(없으면 None)를 그대로 반환한다.
    """
    result = await db.execute(
        select(OrdinanceText).where(OrdinanceText.ordinance_id == ordinance.id)
    )
    cached = result.scalar_one_or_none()
    if cached and cached.full_text:
        return cached

    # serial_no 없으면 API 호출 불가
    if not ordinance.serial_no:
        logger.warning(
            "조례 serial_no 없음, 조례 전문 fetch 불가 (ordinance_id=%s)", ordinance.id
        )
        return cached

    # 법제처 API에서 조례 전문 조회
    from backend.external.moleg_client import MolegClient

    try:
        moleg = MolegClient(api_key=api_key)
        try:
            detail = await moleg.get_ordinance_detail(ordinance.serial_no)
        finally:
            await moleg.close()

        full_text = build_full_text(detail.articles)
        articles_json = [
            {
                "article_no": a.article_no,
                "article_title": a.article_title,
                "article_content": a.article_content,
            }
            for a in detail.articles
        ]

        # DB 저장 (기존 레코드 있으면 업데이트)
        if cached:
            cached.full_text = full_text
            cached.articles_json = articles_json
            cached.fetched_at = datetime.utcnow()
        else:
            cached = OrdinanceText(
                ordinance_id=ordinance.id,
                serial_no=ordinance.serial_no,
                full_text=full_text,
                articles_json=articles_json,
                fetched_at=datetime.utcnow(),
            )
            db.add(cached)
        await db.flush()
        return cached

    except Exception as e:
        logger.warning("조례 전문 fetch 실패 (ordinance_id=%s): %s", ordinance.id, e)
        return cached
