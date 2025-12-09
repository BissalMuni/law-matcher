"""
Dashboard schemas
"""
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel


class DashboardSummary(BaseModel):
    """Dashboard summary"""
    total_ordinances: int
    total_parent_laws: int
    recent_amendments: int
    pending_reviews: int
    need_revision_count: int
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
