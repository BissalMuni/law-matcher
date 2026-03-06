"""
LLM 관련 Pydantic 스키마 - 요청/응답 모델
"""
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field


# === AI 분석 요청/응답 ===

class AiAnalyzeRequest(BaseModel):
    """AI 통합 분석 요청"""
    law_id: int = Field(..., description="분석 대상 상위법령 ID")


class AiAnalyzeResponse(BaseModel):
    """AI 통합 분석 응답"""
    id: int
    ordinance_id: int
    law_id: int
    law_proclaimed_date: Optional[date] = None
    status: str
    summary_text: Optional[str] = None
    review_draft_text: Optional[str] = None
    review_draft_result: Optional[str] = None
    provider_name: str
    model_name: str
    token_usage: Optional[dict] = None
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AiResultItem(BaseModel):
    """AI 분석 결과 항목 (법령별)"""
    id: int
    law_id: int
    law_name: Optional[str] = None
    law_proclaimed_date: Optional[date] = None
    status: str
    summary_text: Optional[str] = None
    review_draft_text: Optional[str] = None
    review_draft_result: Optional[str] = None
    provider_name: str
    model_name: str
    created_at: datetime

    class Config:
        from_attributes = True


class AiResultsResponse(BaseModel):
    """AI 분석 결과 조회 응답"""
    ordinance_id: int
    results: list[AiResultItem]


# === LLM 프로바이더 관리 ===

class LlmProviderResponse(BaseModel):
    """LLM 프로바이더 정보 응답"""
    id: int
    provider_name: str
    display_name: str
    model_name: str
    api_key_env_name: str
    api_key_configured: bool = False  # 런타임 계산
    is_active: bool
    rate_limit_per_minute: int
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LlmProviderListResponse(BaseModel):
    """프로바이더 목록 응답"""
    providers: list[LlmProviderResponse]


class LlmProviderUpdate(BaseModel):
    """프로바이더 설정 변경 요청"""
    model_name: Optional[str] = None
    is_active: Optional[bool] = None
    rate_limit_per_minute: Optional[int] = None


# === AI 분석 통계 ===

class ProviderStats(BaseModel):
    """프로바이더별 통계"""
    count: int
    model: str


class AiAnalyticsResponse(BaseModel):
    """AI 분석 이력/통계 응답"""
    period: dict  # {"start": "2026-02-01", "end": "2026-03-02"}
    total_analyses: int
    success_count: int
    failed_count: int
    draft_adoption_rate: float  # AI 초안 그대로 제출 비율
    draft_modified_rate: float  # AI 초안 수정 후 제출 비율
    draft_unused_rate: float  # AI 분석 후 수동 작성 비율
    average_token_usage: Optional[dict] = None
    by_provider: dict[str, ProviderStats]
