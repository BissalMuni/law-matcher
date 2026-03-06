"""
Article (조문) schemas
"""
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from pydantic import BaseModel


# ============================================================================
# Article Schemas
# ============================================================================

class ArticleBase(BaseModel):
    """Article base schema"""
    article_no: str
    article_title: Optional[str] = None
    article_content: str


class ArticleCreate(ArticleBase):
    """Article creation schema"""
    law_id: int
    paragraphs: Optional[Dict[str, Any]] = None
    content_hash: str
    mst_seq: Optional[int] = None
    jo_seq: Optional[int] = None
    revision_type_detail: Optional[str] = None
    change_flag: Optional[str] = None


class ArticleUpdate(BaseModel):
    """Article update schema"""
    article_title: Optional[str] = None
    article_content: Optional[str] = None
    paragraphs: Optional[Dict[str, Any]] = None
    content_hash: Optional[str] = None
    revision_type_detail: Optional[str] = None
    change_flag: Optional[str] = None


class ArticleResponse(ArticleBase):
    """Article response schema"""
    id: int
    law_id: int
    law_name: Optional[str] = None  # Join from Law
    law_type: Optional[str] = None  # Join from Law
    paragraphs: Optional[Dict[str, Any]] = None
    content_hash: str
    mst_seq: Optional[int] = None
    jo_seq: Optional[int] = None
    revision_type_detail: Optional[str] = None
    change_flag: Optional[str] = None
    ordinance_count: Optional[int] = None  # 연계된 조례 개수
    change_count: Optional[int] = None  # 변경 이력 개수
    last_changed_date: Optional[date] = None  # 최근 변경일
    has_recent_change: Optional[bool] = None  # 30일 이내 변경 여부
    revision_type_detail: Optional[str] = None  # 조문제개정유형
    change_flag: Optional[str] = None  # 조문변경여부 (Y/N)
    last_synced_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ArticleDetailResponse(ArticleResponse):
    """Article detail response (with full info)"""
    pass


class ArticleListResponse(BaseModel):
    """Article list response with pagination"""
    items: List[ArticleResponse]
    total: int
    page: int
    size: int
    pages: int


# ============================================================================
# OrdinanceArticleMapping Schemas
# ============================================================================

class OrdinanceArticleMappingBase(BaseModel):
    """OrdinanceArticleMapping base schema"""
    mapping_reason: Optional[str] = None
    related_article_nos: Optional[str] = None


class OrdinanceArticleMappingCreate(OrdinanceArticleMappingBase):
    """OrdinanceArticleMapping creation schema"""
    ordinance_id: int
    article_id: int


class OrdinanceArticleMappingUpdate(OrdinanceArticleMappingBase):
    """OrdinanceArticleMapping update schema"""
    pass


class OrdinanceArticleMappingResponse(OrdinanceArticleMappingBase):
    """OrdinanceArticleMapping response schema"""
    id: int
    ordinance_id: int
    article_id: int
    ordinance_name: Optional[str] = None  # Join from Ordinance
    ordinance_category: Optional[str] = None  # Join from Ordinance
    department: Optional[str] = None  # Join from Ordinance
    article_no: Optional[str] = None  # Join from Article
    article_title: Optional[str] = None  # Join from Article
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrdinanceArticleMappingListResponse(BaseModel):
    """OrdinanceArticleMapping list response"""
    items: List[OrdinanceArticleMappingResponse]
    total: int


# ============================================================================
# ArticleChange Schemas
# ============================================================================

class ArticleChangeBase(BaseModel):
    """ArticleChange base schema"""
    change_date: date
    change_type: str  # 'created', 'updated', 'deleted'


class ArticleChangeCreate(ArticleChangeBase):
    """ArticleChange creation schema"""
    article_id: int
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    old_hash: Optional[str] = None
    new_hash: Optional[str] = None
    diff_html: Optional[str] = None


class ArticleChangeResponse(ArticleChangeBase):
    """ArticleChange response schema"""
    id: int
    article_id: int
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    old_hash: Optional[str] = None
    new_hash: Optional[str] = None
    diff_html: Optional[str] = None
    detected_at: datetime
    notified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ArticleChangeListResponse(BaseModel):
    """ArticleChange list response"""
    items: List[ArticleChangeResponse]
    total: int


# ============================================================================
# Sync Schemas
# ============================================================================

class ArticleSyncRequest(BaseModel):
    """Article sync request schema"""
    law_ids: Optional[List[int]] = None  # 특정 법령만 동기화 (optional)
    force: bool = False  # 강제 동기화 여부


class ArticleSyncResponse(BaseModel):
    """Article sync response schema"""
    success: bool
    synced_articles: int
    created: int
    updated: int
    deleted: int
    changes_detected: int
    message: str


# ============================================================================
# Query Schemas
# ============================================================================

class ArticleListParams(BaseModel):
    """Article list query parameters"""
    page: int = 1
    size: int = 20
    law_id: Optional[int] = None  # 법령 ID 필터
    search: Optional[str] = None  # 조문번호 또는 제목 검색
    has_ordinance: Optional[bool] = None  # 연계 조례 존재 여부
    changed_since: Optional[date] = None  # 특정 일자 이후 변경된 조문


class ArticleCountParams(BaseModel):
    """Article count query parameters"""
    law_id: Optional[int] = None
    has_ordinance: Optional[bool] = None
    changed_since: Optional[date] = None


# ============================================================================
# Phase 4: 추가 API Schemas
# ============================================================================

class BulkMappingRequest(BaseModel):
    """대량 매핑 요청"""
    mappings: List[Dict[str, int]]  # [{"article_id": 1, "ordinance_id": 2}, ...]
    mapping_reason: Optional[str] = None  # notes -> mapping_reason


class BulkMappingResponse(BaseModel):
    """대량 매핑 응답"""
    success: bool
    created_count: int
    failed_count: int
    message: str
    failed_items: Optional[List[Dict[str, Any]]] = None


class RevisionNeededOrdinanceItem(BaseModel):
    """개정 검토 필요 조례 항목"""
    ordinance_id: int
    ordinance_name: str
    ordinance_category: str
    department: str
    article_id: int
    article_no: str
    article_title: Optional[str] = None
    law_name: str
    change_date: date
    detected_at: datetime
    change_type: str
    diff_html: Optional[str] = None
    affected_article_count: Optional[int] = None  # related_articles가 없는 경우 변경된 조문 개수

    class Config:
        from_attributes = True


class RevisionNeededOrdinanceListResponse(BaseModel):
    """개정 검토 필요 조례 목록 응답"""
    items: List[RevisionNeededOrdinanceItem]
    total: int
    page: int
    size: int


class AutoMappingRecommendation(BaseModel):
    """자동 매핑 추천 항목"""
    article_id: int
    article_no: str
    article_title: Optional[str] = None
    article_content: str
    ordinance_id: int
    ordinance_name: str
    ordinance_category: str
    similarity_score: float  # 0.0 ~ 1.0
    reason: str  # 추천 이유


class AutoMappingRecommendationResponse(BaseModel):
    """자동 매핑 추천 응답"""
    recommendations: List[AutoMappingRecommendation]
    total: int
