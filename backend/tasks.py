"""
Celery tasks for Law Matcher
"""
import asyncio
from typing import Any, Optional

from sqlalchemy import select

from backend.celery_app import celery_app
from backend.core.database import async_session
from backend.models.law import Law
from backend.services.law_sync_service import LawSyncService


async def _run_law_sync(law_ids: Optional[list[str]]) -> dict[str, Any]:
    async with async_session() as db:
        service = LawSyncService(db)

        if not law_ids:
            return await service.update_all_law_info()

        parsed_ids = []
        for value in law_ids:
            try:
                parsed_ids.append(int(value))
            except (TypeError, ValueError):
                continue

        if not parsed_ids:
            return {"total_laws": 0, "updated": 0, "failed": 0}

        stmt = select(Law).where((Law.id.in_(parsed_ids)) | (Law.law_id.in_(parsed_ids)))
        result = await db.execute(stmt)
        target_laws = list(result.scalars().all())

        updated = 0
        failed = 0
        for law in target_laws:
            try:
                api_results, _ = await service.search_laws(query=law.law_name, display=10)
                exact_match = next((item for item in api_results if item.law_name == law.law_name), None)
                if exact_match:
                    await service.sync_law(exact_match)
                    updated += 1
                else:
                    failed += 1
            except Exception:
                failed += 1

        await db.commit()
        return {
            "total_laws": len(target_laws),
            "updated": updated,
            "failed": failed,
        }


@celery_app.task(name="backend.tasks.sync_laws")
def sync_laws(law_ids: Optional[list[str]] = None) -> dict[str, Any]:
    """Sync all laws or the specified law ids."""
    return asyncio.run(_run_law_sync(law_ids))


@celery_app.task(name="backend.tasks.sync_all_laws_daily")
def sync_all_laws_daily() -> dict[str, Any]:
    """Daily scheduled law sync task."""
    return asyncio.run(_run_law_sync(None))
