"""
Celery tasks for Law Matcher
"""
from celery import Celery

from backend.core.config import settings

app = Celery(
    "law_matcher",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Seoul",
    enable_utc=True,
)


@app.task
def example_task():
    """Example task - replace with your actual tasks"""
    return {"status": "success"}
