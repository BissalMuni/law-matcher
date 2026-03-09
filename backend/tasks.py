"""
Celery tasks for Law Matcher

파이프라인:
1. sync_all_laws_daily (Celery Beat - 매일 9시)
   └─ 법령(Law) 메타데이터 동기화 (LawSyncService.update_all_law_info)
"""
import asyncio
import logging
from typing import Any, Optional

from sqlalchemy import select

from backend.celery_app import celery_app
from backend.core.database import async_session
from backend.models.law import Law

logger = logging.getLogger(__name__)


async def _run_law_sync(law_ids: Optional[list[str]]) -> dict[str, Any]:
    """법령 메타데이터 동기화 실행"""
    from backend.services.law_sync_service import LawSyncService

    async with async_session() as db:
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


@celery_app.task(name="backend.tasks.sync_laws")
def sync_laws(law_ids: Optional[list[str]] = None) -> dict[str, Any]:
    """특정 법령 또는 전체 법령 동기화 (법령 메타데이터)."""
    return asyncio.run(_run_law_sync(law_ids))


@celery_app.task(name="backend.tasks.sync_all_laws_daily")
def sync_all_laws_daily() -> dict[str, Any]:
    """매일 9:00 자동 실행 - 전체 법령 동기화."""
    return asyncio.run(_run_law_sync(None))
