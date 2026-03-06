"""
Redis 기반 LLM Rate Limiter
시스템 전체 분당 최대 N회 LLM 호출 제한
"""
import logging

import redis.asyncio as aioredis

from backend.core.config import settings

logger = logging.getLogger(__name__)

RATE_LIMIT_KEY = "llm:rate_limit"


class RateLimitExceededError(Exception):
    """Rate Limit 초과"""
    pass


async def check_rate_limit(rate_limit_per_minute: int) -> None:
    """
    Redis INCR + EXPIRE 패턴으로 분당 호출 수를 제한한다.
    초과 시 RateLimitExceededError 발생.
    """
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        count = await r.incr(RATE_LIMIT_KEY)
        if count == 1:
            await r.expire(RATE_LIMIT_KEY, 60)  # 1분 TTL
        if count > rate_limit_per_minute:
            logger.warning(
                f"LLM Rate Limit 초과: {count}/{rate_limit_per_minute} per minute"
            )
            raise RateLimitExceededError(
                "AI 분석 요청이 제한을 초과했습니다. 잠시 후 다시 시도해 주세요"
            )
    finally:
        await r.aclose()
