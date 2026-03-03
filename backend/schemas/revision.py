"""
Revision detection schemas
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DetectionMethodEnum(str, Enum):
    proclaimed_date = "proclaimed_date"
    article_change = "article_change"
    revision_reason = "revision_reason"


class RevisionReasonOut(BaseModel):
    law_id: int
    law_mst: str
    revision_reason: Optional[str] = None
    amendment_content: Optional[str] = None
    extracted_articles: List[str] = Field(default_factory=list)
    fetched_at: datetime

    class Config:
        from_attributes = True


class DetectionResultOut(BaseModel):
    method: DetectionMethodEnum
    needs_revision: bool
    detail: Dict[str, Any] = Field(default_factory=dict)
    detected_at: datetime


class DetectionNotificationOut(BaseModel):
    message: str
    changed_methods: List[str] = Field(default_factory=list)
    created_at: str


class DetectionResultsOut(BaseModel):
    ordinance_id: int
    ordinance_name: str
    results: List[DetectionResultOut] = Field(default_factory=list)
    notification: Optional[DetectionNotificationOut] = None


class DetectRequest(BaseModel):
    methods: Optional[List[DetectionMethodEnum]] = None
