"""
Celery application configuration.
"""
from celery import Celery

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
    "check-sync-schedule": {
        "task": "backend.tasks.check_sync_schedule",
        "schedule": 300.0,  # 5분마다 DB에서 자동 동기화 설정 확인
    },
}

# Celery CLI default variable name compatibility.
app = celery_app
