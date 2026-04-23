"""
AI 분석 API 엔드포인트
POST /ordinances/{id}/ai-analyze — Celery 태스크 enqueue (202 Accepted, task_id 반환)
GET  /ordinances/ai-analyze/tasks/{task_id} — 태스크 상태/결과 폴링
GET  /ordinances/{id}/ai-results — 저장된 AI 분석 결과 조회
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db, get_current_user
from backend.models.user import User
from backend.schemas.llm import (
    AiAnalyzeRequest,
    AiAnalyzeResponse,
    AiAnalyzeTaskAccepted,
    AiAnalyzeTaskStatus,
    AiResultsResponse,
    AiResultItem,
)
from backend.services.llm_analysis_service import LlmAnalysisService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/{ordinance_id}/ai-analyze",
    response_model=AiAnalyzeTaskAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def ai_analyze(
    ordinance_id: int,
    body: AiAnalyzeRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    AI 통합 분석 요청 — Celery 백그라운드 태스크로 분리.
    즉시 202 Accepted + task_id를 반환하며, 클라이언트는
    GET /ordinances/ai-analyze/tasks/{task_id} 로 상태/결과를 폴링한다.
    """
    from backend.tasks import ai_analyze_task

    force = bool(body.force) and current_user.user_type == "ADMIN"
    async_result = ai_analyze_task.delay(ordinance_id, body.law_id, force)
    response.status_code = status.HTTP_202_ACCEPTED
    return AiAnalyzeTaskAccepted(task_id=async_result.id, state="PENDING")


@router.get(
    "/ai-analyze/tasks/{task_id}",
    response_model=AiAnalyzeTaskStatus,
)
async def ai_analyze_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    """AI 분석 Celery 태스크 상태/결과 폴링."""
    from backend.celery_app import celery_app

    async_result = celery_app.AsyncResult(task_id)
    state = async_result.state  # PENDING | STARTED | RETRY | SUCCESS | FAILURE

    if state in ("PENDING", "STARTED", "RETRY"):
        return AiAnalyzeTaskStatus(task_id=task_id, state=state, ready=False)

    if state == "FAILURE":
        # 예기치 못한 예외 — 워커가 raise 한 경우
        einfo = async_result.info
        error_detail = str(einfo) if einfo else "AI 분석 태스크 실패"
        return AiAnalyzeTaskStatus(
            task_id=task_id,
            state=state,
            ready=True,
            error_code="UNEXPECTED",
            error_detail=error_detail,
            http_status=502,
        )

    # SUCCESS — 태스크 본체가 dict 를 반환. 성공/실패 분기.
    payload = async_result.result or {}
    if isinstance(payload, dict) and payload.get("ok"):
        return AiAnalyzeTaskStatus(
            task_id=task_id,
            state=state,
            ready=True,
            result=AiAnalyzeResponse.model_validate(payload["result"]),
            http_status=200,
        )

    # 앱 레벨 에러 (ConflictError / RateLimit / ValueError 등)
    return AiAnalyzeTaskStatus(
        task_id=task_id,
        state=state,
        ready=True,
        error_code=payload.get("error_code", "UNEXPECTED"),
        error_detail=payload.get("error_detail"),
        existing_result_id=payload.get("existing_result_id"),
        http_status=payload.get("status_code", 500),
    )


@router.delete("/{ordinance_id}/ai-results/{law_id}")
async def delete_ai_results(
    ordinance_id: int,
    law_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """AI 분석 결과 삭제 — 해당 조례+법령의 모든 분석 결과 삭제"""
    from sqlalchemy import select, delete
    from backend.models.llm_analysis_result import LlmAnalysisResult

    result = await db.execute(
        delete(LlmAnalysisResult).where(
            LlmAnalysisResult.ordinance_id == ordinance_id,
            LlmAnalysisResult.law_id == law_id,
        )
    )
    await db.commit()
    return {"deleted": result.rowcount}


@router.get("/{ordinance_id}/ai-results", response_model=AiResultsResponse)
async def get_ai_results(
    ordinance_id: int,
    law_id: Optional[int] = Query(None, description="특정 법령의 결과만 조회"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """AI 분석 결과 조회 — 법령별 결과 목록 반환"""
    service = LlmAnalysisService(db)
    results = await service.get_analysis_results(ordinance_id, law_id)

    # 법령명 조회를 위해 law 정보 추가
    from sqlalchemy import select
    from backend.models.law import Law

    items = []
    for r in results:
        law_name = None
        if r.law_id:
            law_result = await db.execute(
                select(Law.law_name).where(Law.id == r.law_id)
            )
            law_name = law_result.scalar_one_or_none()

        items.append(AiResultItem(
            id=r.id,
            law_id=r.law_id,
            law_name=law_name,
            law_proclaimed_date=r.law_proclaimed_date,
            status=r.status,
            summary_text=r.summary_text,
            review_draft_text=r.review_draft_text,
            review_draft_result=r.review_draft_result,
            affected_articles_json=r.affected_articles_json,
            provider_name=r.provider_name,
            model_name=r.model_name,
            created_at=r.created_at,
        ))

    return AiResultsResponse(ordinance_id=ordinance_id, results=items)
