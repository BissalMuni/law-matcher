"""
AI 분석 API 엔드포인트
POST /ordinances/{id}/ai-analyze — AI 통합 분석 실행
GET /ordinances/{id}/ai-results — AI 분석 결과 조회
"""
import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db, get_current_user
from backend.models.user import User
from backend.schemas.llm import AiAnalyzeRequest, AiAnalyzeResponse, AiResultsResponse, AiResultItem
from backend.services.llm_analysis_service import (
    LlmAnalysisService,
    ConflictError,
)
from backend.services.llm_client import LlmServiceUnavailableError
from backend.services.llm_rate_limiter import RateLimitExceededError
from backend.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/{ordinance_id}/ai-analyze", response_model=AiAnalyzeResponse)
async def ai_analyze(
    ordinance_id: int,
    body: AiAnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    AI 통합 분석 실행 — 1회 호출로 개정내용 요약 + 검토의견 초안 동시 생성
    30초 타임아웃, 동기 응답
    """
    service = LlmAnalysisService(db)

    try:
        result = await asyncio.wait_for(
            service.analyze_ordinance(ordinance_id, body.law_id),
            timeout=settings.LLM_TIMEOUT + 5,  # 약간의 여유
        )
        await db.commit()
        return result

    except asyncio.TimeoutError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI 분석 시간이 초과되었습니다. 다시 시도해 주세요",
        )
    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"detail": str(e), "existing_result_id": e.existing_result_id},
        )
    except LlmServiceUnavailableError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except RateLimitExceededError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
        )
    except ValueError as e:
        error_msg = str(e)
        if "찾을 수 없습니다" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=error_msg
            )
        elif "연결 정보" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg
            )
        elif "제개정이유" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error_msg
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg
            )
    except Exception as e:
        await db.rollback()
        logger.error(f"AI 분석 예외: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI 분석을 수행할 수 없습니다. 직접 검토해 주세요",
        )


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
            provider_name=r.provider_name,
            model_name=r.model_name,
            created_at=r.created_at,
        ))

    return AiResultsResponse(ordinance_id=ordinance_id, results=items)
