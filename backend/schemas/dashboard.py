"""
Dashboard schemas
"""
from typing import List, Optional
from datetime import datetime, date
from pydantic import BaseModel


class DashboardSummary(BaseModel):
    """Dashboard summary"""
    total_ordinances: int
    total_parent_laws: int
    recent_amendments: int
    pending_reviews: int
    need_revision_count: int
    revision_needs_action_count: int  # revision needed (red)
    revision_completed_count: int  # revision completed (green)
    last_sync_at: Optional[datetime] = None


class RecentAmendmentItem(BaseModel):
    """Recent amendment item"""
    id: int
    law_name: str
    change_type: str
    detected_at: datetime
    affected_ordinances: int


class RecentAmendments(BaseModel):
    """Recent amendments response"""
    items: List[RecentAmendmentItem]


class PendingReviewItem(BaseModel):
    """Pending review item"""
    id: int
    ordinance_name: str
    law_name: str
    urgency: str
    created_at: datetime


class PendingReviews(BaseModel):
    """Pending reviews response"""
    items: List[PendingReviewItem]


class RevisionTypeCount(BaseModel):
    """개정구분별 건수"""
    revision_type: str
    count: int


class LatestSyncStats(BaseModel):
    """최근 동기화 통계"""
    sync_date: Optional[datetime] = None
    total_laws: int = 0
    by_revision_type: List[RevisionTypeCount] = []


class RevisionNeededItem(BaseModel):
    """Revision needed item"""
    ordinance_id: int
    ordinance_name: str
    ordinance_revision_date: Optional[date]
    law_id: int
    law_name: str
    law_type: str
    law_proclaimed_date: Optional[date]
    days_diff: int
    revision_status: str
    department: Optional[str]

    class Config:
        from_attributes = True


class RevisionNeededListResponse(BaseModel):
    """Revision needed list response"""
    total: int
    needs_revision_count: int
    completed_count: int
    items: List[RevisionNeededItem]
