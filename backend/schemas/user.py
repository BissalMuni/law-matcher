"""
User schemas
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """User base schema"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    full_name: Optional[str] = Field(None, max_length=100)
    user_type: str = Field(..., pattern="^(DEPARTMENT|GENERAL)$")
    department_id: Optional[int] = None


class UserCreate(UserBase):
    """User create schema"""
    password: str = Field(..., min_length=8, max_length=100)


class UserUpdate(BaseModel):
    """User update schema"""
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    full_name: Optional[str] = Field(None, max_length=100)
    password: Optional[str] = Field(None, min_length=8, max_length=100)
    user_type: Optional[str] = Field(None, pattern="^(DEPARTMENT|GENERAL)$")
    department_id: Optional[int] = None
    is_active: Optional[bool] = None


class UserBriefResponse(BaseModel):
    """User brief response - for nested objects"""
    id: int
    username: str
    full_name: Optional[str] = None
    user_type: str

    class Config:
        from_attributes = True


class UserResponse(UserBase):
    """User response"""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserWithDepartmentResponse(UserResponse):
    """User response with department info"""
    department_name: Optional[str] = None
    department_code: Optional[str] = None

    class Config:
        from_attributes = True
