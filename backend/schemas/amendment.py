"""
Amendment schemas
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class ChangeSummary(BaseModel):
    """Change summary"""
    added: List[str] = []
    modified: List[Dict[str, Any]] = []
    deleted: List[str] = []


class AmendmentResponse(BaseModel):
    """Amendment response"""
    id: int
    law_id: str
    law_name: str
    change_type: str
    change_summary: Optional[ChangeSummary] = None
    detected_at: datetime
    processed: bool

    class Config:
        from_attributes = True


class AmendmentListResponse(BaseModel):
    """Amendment list response"""
    total: int
    page: int
    size: int
    items: List[AmendmentResponse]


class ImpactAnalysisResponse(BaseModel):
    """Impact analysis response"""
    amendment_id: int
    affected_ordinances: int
    need_revision_count: int
    reviews_created: int
