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
