"""
Redis 기반 LLM Rate Limiter
시스템 전체 분당 최대 N회 LLM 호출 제한
배치 처리 시 대기 기반으로 동작하여 처리 중단 방지
"""
import asyncio
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


async def wait_for_rate_limit(rate_limit_per_minute: int, max_wait: float = 65.0) -> None:
    """
    배치 처리용: Rate Limit 초과 시 슬롯이 빌 때까지 대기.
    max_wait 초과 시 RateLimitExceededError 발생.
    """
    waited = 0.0
    interval = 1.0
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        while True:
            count = await r.incr(RATE_LIMIT_KEY)
            if count == 1:
                await r.expire(RATE_LIMIT_KEY, 60)
            if count <= rate_limit_per_minute:
                return  # 슬롯 확보 성공
            # 슬롯 초과 — 카운터 롤백 후 대기
            await r.decr(RATE_LIMIT_KEY)
            if waited >= max_wait:
                raise RateLimitExceededError(
                    f"Rate Limit 대기 시간 초과 ({max_wait}초)"
                )
            ttl = await r.ttl(RATE_LIMIT_KEY)
            wait_time = min(interval, max(1, ttl)) if ttl > 0 else interval
            logger.debug(f"Rate Limit 대기 중... ({waited:.0f}s/{max_wait}s, TTL={ttl}s)")
            await asyncio.sleep(wait_time)
            waited += wait_time
    finally:
        await r.aclose()
