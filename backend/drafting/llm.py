"""입안심사 전용 Anthropic 호출 헬퍼.

law-matcher의 settings.ANTHROPIC_API_KEY / DRAFTING_MODEL 설정을 재사용한다.
- stream_text(): 작성(draft) SSE 스트리밍
- DraftingLLM.call(): 검증 매트릭스용 JSON 단발 호출 (재시도 + 동시성 제어)

law-ebansimsa pipeline.review.llm_client + api.routers.draft.get_streamer 포팅.
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator

from backend.core.config import settings

logger = logging.getLogger(__name__)


def _api_key() -> str:
    if not settings.ANTHROPIC_API_KEY:
        raise RuntimeError(
            "ANTHROPIC_API_KEY가 설정되지 않았습니다. 입안심사 AI 기능을 쓰려면 .env에 설정하세요."
        )
    return settings.ANTHROPIC_API_KEY


async def stream_text(system: str, user: str, *, max_tokens: int = 2048) -> AsyncIterator[str]:
    """작성용 스트리밍 — 텍스트 델타를 순차로 yield 한다."""
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=_api_key(), timeout=settings.LLM_TIMEOUT)
    async with client.messages.stream(
        model=settings.DRAFTING_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    ) as stream:
        async for text in stream.text_stream:
            yield text


class DraftingLLM:
    """검증 매트릭스용 비동기 JSON 호출 클라이언트 (세마포어 + 지수 백오프)."""

    def __init__(self, max_retries: int = 3, concurrency: int | None = None):
        import anthropic

        self.client = anthropic.AsyncAnthropic(
            api_key=_api_key(), timeout=settings.LLM_TIMEOUT
        )
        self.model = settings.DRAFTING_MODEL
        self.fast_model = settings.DRAFTING_FAST_MODEL
        self.max_retries = max_retries
        self._semaphore = asyncio.Semaphore(concurrency or settings.DRAFTING_CONCURRENCY)

    async def call(
        self, system: str, user: str, *, use_fast: bool = False, max_tokens: int = 1024
    ) -> dict:
        """단일 LLM 호출. 파싱된 JSON dict 반환. 실패 시 {"raw"|"error": ...}."""
        import anthropic

        model = self.fast_model if use_fast else self.model
        async with self._semaphore:
            for attempt in range(self.max_retries):
                try:
                    response = await self.client.messages.create(
                        model=model,
                        max_tokens=max_tokens,
                        system=system,
                        messages=[{"role": "user", "content": user}],
                    )
                    text = response.content[0].text.strip()
                    if text.startswith("```"):
                        text = text.split("\n", 1)[1]
                        if text.endswith("```"):
                            text = text[:-3].strip()
                    try:
                        return json.loads(text)
                    except json.JSONDecodeError:
                        return {"raw": text}
                except anthropic.RateLimitError:
                    wait = 2 ** (attempt + 1)
                    logger.warning(f"Rate limit, waiting {wait}s (attempt {attempt + 1})")
                    await asyncio.sleep(wait)
                except anthropic.APIError as e:
                    if attempt == self.max_retries - 1:
                        logger.error(f"API error after {self.max_retries} attempts: {e}")
                        return {"error": str(e)}
                    wait = 2 ** attempt
                    logger.warning(f"API error, retrying in {wait}s: {e}")
                    await asyncio.sleep(wait)
        return {"error": "max retries exceeded"}
