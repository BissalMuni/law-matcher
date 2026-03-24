"""
Celery tasks for Law Matcher

파이프라인:
1. sync_all_laws_daily (Celery Beat - 매일 9시)
   └─ 법령(Law) 메타데이터 동기화 (LawSyncService.sync_all_laws_with_progress)
2. sync_laws_background — 프론트 "법령 동기화" 버튼 → 백그라운드 실행 + Redis 진행 상황 저장
"""
import asyncio
import json
import logging
from typing import Any, Optional

from sqlalchemy import select

from backend.celery_app import celery_app
from backend.core.config import settings
from backend.core.database import async_session
from backend.models.law import Law

logger = logging.getLogger(__name__)

SYNC_PROGRESS_KEY = "law_sync:progress"
SYNC_PROGRESS_TTL = 3600  # 1시간 후 자동 삭제


def _get_redis():
    """Redis 클라이언트 반환 (동기)"""
    import redis
    return redis.Redis.from_url(settings.CELERY_BROKER_URL, decode_responses=True)


def _save_progress(r, data: dict):
    """Redis에 진행 상황 저장"""
    r.set(SYNC_PROGRESS_KEY, json.dumps(data, ensure_ascii=False, default=str))
    r.expire(SYNC_PROGRESS_KEY, SYNC_PROGRESS_TTL)


async def _run_law_sync_with_progress() -> dict[str, Any]:
    """sync_all_laws_with_progress 제너레이터를 소비하며 Redis에 진행 상황 기록"""
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
    from backend.services.law_sync_service import LawSyncService

    r = _get_redis()
    result_data = {}

    # 매 태스크마다 새 엔진 생성 (asyncio.run()의 새 이벤트 루프와 호환)
    task_engine = create_async_engine(settings.DATABASE_URL, future=True)
    task_session = async_sessionmaker(task_engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with task_session() as db:
            service = LawSyncService(db)
            async for event in service.sync_all_laws_with_progress():
                event_type = event.get("type")

                if event_type == "start":
                    _save_progress(r, {
                        "status": "RUNNING",
                        "current": 0,
                        "total": event.get("total", 0),
                        "law_name": "",
                        "message": event.get("message", ""),
                        "changed_laws": [],
                        "failed": 0,
                        "updated": 0,
                    })

                elif event_type == "progress":
                    # 기존 데이터 읽어서 업데이트 (changed_laws 보존)
                    raw = r.get(SYNC_PROGRESS_KEY)
                    prev = json.loads(raw) if raw else {}
                    prev.update({
                        "status": "RUNNING",
                        "current": event.get("current", 0),
                        "total": event.get("total", 0),
                        "law_name": event.get("law_name", ""),
                        "step": event.get("status", ""),
                        "message": event.get("message", ""),
                    })
                    _save_progress(r, prev)

                elif event_type == "changed":
                    raw = r.get(SYNC_PROGRESS_KEY)
                    prev = json.loads(raw) if raw else {}
                    changed = prev.get("changed_laws", [])
                    changed.append(event.get("law", {}))
                    prev["changed_laws"] = changed
                    _save_progress(r, prev)

                elif event_type == "error":
                    raw = r.get(SYNC_PROGRESS_KEY)
                    prev = json.loads(raw) if raw else {}
                    prev["message"] = event.get("message", "")
                    _save_progress(r, prev)

                elif event_type == "complete":
                    result_data = {
                        "status": "COMPLETED",
                        "current": event.get("total", 0),
                        "total": event.get("total", 0),
                        "updated": event.get("updated", 0),
                        "failed": event.get("failed", 0),
                        "changed_count": event.get("changed_count", 0),
                        "changed_laws": event.get("changed_laws", []),
                        "flagged_ordinances": event.get("flagged_ordinances", 0),
                        "message": event.get("message", ""),
                        "law_name": "",
                    }
                    _save_progress(r, result_data)
    finally:
        await task_engine.dispose()

    return result_data


async def _run_law_sync(law_ids: Optional[list[str]]) -> dict[str, Any]:
    """법령 메타데이터 동기화 실행"""
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
    from backend.services.law_sync_service import LawSyncService

    task_engine = create_async_engine(settings.DATABASE_URL, future=True)
    task_session = async_sessionmaker(task_engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with task_session() as db:
            law_service = LawSyncService(db)

            if not law_ids:
                law_sync_result = await law_service.update_all_law_info()
            else:
                parsed_ids = []
                for value in law_ids:
                    try:
                        parsed_ids.append(int(value))
                    except (TypeError, ValueError):
                        continue

                if not parsed_ids:
                    return {"total_laws": 0, "law_updated": 0, "law_failed": 0}

                stmt = select(Law).where(
                    (Law.id.in_(parsed_ids)) | (Law.law_id.in_(parsed_ids))
                )
                result = await db.execute(stmt)
                target_laws = list(result.scalars().all())

                updated = 0
                failed = 0
                for law in target_laws:
                    try:
                        api_results, _ = await law_service.search_laws(
                            query=law.law_name, display=10
                        )
                        exact_match = next(
                            (item for item in api_results if item.law_name == law.law_name),
                            None,
                        )
                        if exact_match:
                            await law_service.sync_law(exact_match)
                            updated += 1
                        else:
                            failed += 1
                    except Exception:
                        failed += 1

                await db.commit()
                law_sync_result = {
                    "total_laws": len(target_laws),
                    "updated": updated,
                    "failed": failed,
                }

            return {
                "total_laws": law_sync_result.get("total_laws", 0),
                "law_updated": law_sync_result.get("updated", 0),
                "law_failed": law_sync_result.get("failed", 0),
            }
    finally:
        await task_engine.dispose()


@celery_app.task(name="backend.tasks.sync_laws")
def sync_laws(law_ids: Optional[list[str]] = None) -> dict[str, Any]:
    """특정 법령 또는 전체 법령 동기화 (법령 메타데이터)."""
    return asyncio.run(_run_law_sync(law_ids))


@celery_app.task(name="backend.tasks.sync_laws_background")
def sync_laws_background() -> dict[str, Any]:
    """전체 법령 동기화 (백그라운드 + Redis 진행 상황 저장)."""
    r = _get_redis()
    try:
        _save_progress(r, {
            "status": "RUNNING",
            "current": 0,
            "total": 0,
            "law_name": "",
            "message": "동기화 시작 중...",
            "changed_laws": [],
            "failed": 0,
            "updated": 0,
        })
        return asyncio.run(_run_law_sync_with_progress())
    except Exception as e:
        logger.error("법령 동기화 태스크 실패: %s", e, exc_info=True)
        _save_progress(r, {
            "status": "FAILED",
            "message": f"동기화 실패: {str(e)}",
            "current": 0,
            "total": 0,
            "changed_laws": [],
            "failed": 0,
            "updated": 0,
        })
        raise


@celery_app.task(name="backend.tasks.sync_all_laws_daily")
def sync_all_laws_daily() -> dict[str, Any]:
    """매일 9:00 자동 실행 - 전체 법령 동기화."""
    return asyncio.run(_run_law_sync_with_progress())
