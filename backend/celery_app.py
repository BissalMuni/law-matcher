"""
Celery application configuration.
"""
from celery import Celery
from celery.schedules import crontab

from backend.core.config import settings

celery_app = Celery(
    "law_matcher",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["backend.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Seoul",
    enable_utc=True,
    task_track_started=True,
)

celery_app.conf.beat_schedule = {
    "sync-all-laws-daily": {
        "task": "backend.tasks.sync_all_laws_daily",
        "schedule": crontab(
            hour=settings.CELERY_BEAT_SYNC_HOUR,
            minute=settings.CELERY_BEAT_SYNC_MINUTE,
        ),
    },
}

# Celery CLI default variable name compatibility.
app = celery_app
