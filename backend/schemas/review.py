"""
Review schemas
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class AffectedArticle(BaseModel):
    """Affected article"""
    article_no: str
    impact_type: str
    details: Optional[Dict[str, Any]] = None


class ReviewResponse(BaseModel):
    """Review response"""
    id: int
    amendment_id: int
    ordinance_id: int
    ordinance_name: Optional[str] = None
    law_name: Optional[str] = None
    need_revision: bool
    revision_urgency: Optional[str] = None
    affected_articles: Optional[List[AffectedArticle]] = None
    reason: Optional[str] = None
    recommendation: Optional[str] = None
    status: str
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ReviewListResponse(BaseModel):
    """Review list response"""
    total: int
    page: int
    size: int
    items: List[ReviewResponse]


class ReviewUpdate(BaseModel):
    """Review update request"""
    status: Optional[str] = None
    reviewed_by: Optional[str] = None
    reason: Optional[str] = None
    recommendation: Optional[str] = None


class ReviewReportItem(BaseModel):
    """Review report item"""
    ordinance_name: str
    department: Optional[str]
    law_name: str
    urgency: str
    affected_count: int
    reason: Optional[str]


class ReviewReportResponse(BaseModel):
    """Review report response"""
    generated_at: datetime
    total_need_revision: int
    by_urgency: Dict[str, int]
    items: List[ReviewReportItem]
