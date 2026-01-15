"""
Department schemas
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


class DepartmentBase(BaseModel):
    """Department base schema"""
    code: str
    name: str
    parent_code: Optional[str] = None
    phone: Optional[str] = None


class DepartmentCreate(DepartmentBase):
    """Department create schema"""
    pass


class DepartmentUpdate(BaseModel):
    """Department update schema"""
    name: Optional[str] = None
    parent_code: Optional[str] = None
    phone: Optional[str] = None


class DepartmentResponse(DepartmentBase):
    """Department response"""
    id: int
    created_at: datetime
    updated_at: datetime
    ordinance_count: Optional[int] = None

    class Config:
        from_attributes = True


class DepartmentListResponse(BaseModel):
    """Department list response"""
    total: int
    page: int
    size: int
    items: List[DepartmentResponse]


class DepartmentSummary(BaseModel):
    """Department summary for dashboard"""
    id: int
    code: str
    name: str
    ordinance_count: int
    pending_review_count: int

    class Config:
        from_attributes = True


class DepartmentInputStats(BaseModel):
    """Department statistics for parent law input progress"""
    id: int
    name: str
    total_ordinances: int  # 총 자치법규 수
    ordinances_with_laws: int  # 상위법령 입력 완료 수
    ordinances_without_laws: int  # 상위법령 미입력 수
    progress_rate: float  # 진행률 (%)

    class Config:
        from_attributes = True


class DepartmentInputStatsResponse(BaseModel):
    """Overall statistics response with department breakdown"""
    total_ordinances: int
    total_with_laws: int
    total_without_laws: int
    overall_progress_rate: float
    departments: List[DepartmentInputStats]
