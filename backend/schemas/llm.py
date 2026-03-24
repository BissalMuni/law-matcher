"""
LLM 관련 Pydantic 스키마 - 요청/응답 모델
"""
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field


# === 개정 필요 조례 조문 분석 ===

class AffectedOrdinanceArticle(BaseModel):
    """개정 필요 조례 조문 항목"""
    article_no: str = Field(..., description="조문번호 (예: 제3조)")
    article_title: Optional[str] = Field(None, description="조문 제목")
    current_content_summary: Optional[str] = Field(None, description="현재 조문 내용 요약")
    issue: Optional[str] = Field(None, description="상위법령 개정으로 인한 문제점")
    recommendation: Optional[str] = Field(None, description="구체적인 개정 권고")


# === AI 분석 요청/응답 ===

class AiAnalyzeRequest(BaseModel):
    """AI 통합 분석 요청"""
    law_id: int = Field(..., description="분석 대상 상위법령 ID")
    force: bool = Field(False, description="기존 성공 결과 삭제 후 재분석 (관리자 전용)")


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
    affected_articles_json: Optional[List[AffectedOrdinanceArticle]] = None
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
    affected_articles_json: Optional[List[AffectedOrdinanceArticle]] = None
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

class AvailableModel(BaseModel):
    """선택 가능한 모델 항목"""
    id: str
    name: str


class LlmProviderResponse(BaseModel):
    """LLM 프로바이더 정보 응답"""
    id: int
    provider_name: str
    display_name: str
    model_name: str
    api_key_env_name: str
    api_key_configured: bool = False  # 런타임 계산
    api_key_source: str = "none"  # 'env' | 'db' | 'none'
    is_active: bool
    rate_limit_per_minute: int
    available_models: list[AvailableModel] = []
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LlmProviderListResponse(BaseModel):
    """프로바이더 목록 응답"""
    providers: list[LlmProviderResponse]


class LlmProviderUpdate(BaseModel):
    """프로바이더 설정 변경 요청"""
    model_name: Optional[str] = None
    api_key: Optional[str] = None  # DB에 저장할 API 키
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
