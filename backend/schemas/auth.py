"""
Authentication schemas
"""
from typing import Optional
from pydantic import BaseModel, EmailStr, Field

from backend.schemas.user import UserResponse, UserWithDepartmentResponse


class RegisterRequest(BaseModel):
    """User registration request"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = Field(None, max_length=100)
    user_type: str = Field(..., pattern="^(DEPARTMENT|GENERAL)$")
    department_id: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "username": "johndoe",
                "password": "SecurePass123!",
                "full_name": "John Doe",
                "user_type": "DEPARTMENT",
                "department_id": 1
            }
        }


class LoginRequest(BaseModel):
    """User login request"""
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=1, max_length=100)

    class Config:
        json_schema_extra = {
            "example": {
                "username": "johndoe",
                "password": "SecurePass123!"
            }
        }


class TokenResponse(BaseModel):
    """JWT token response with department info"""
    access_token: str
    token_type: str = "bearer"
    user: UserWithDepartmentResponse

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user": {
                    "id": 1,
                    "email": "user@example.com",
                    "username": "johndoe",
                    "full_name": "John Doe",
                    "user_type": "DEPARTMENT",
                    "department_id": 1,
                    "is_active": True,
                    "created_at": "2024-01-01T00:00:00",
                    "updated_at": "2024-01-01T00:00:00"
                }
            }
        }


class PasswordChangeRequest(BaseModel):
    """Password change request"""
    current_password: str = Field(..., min_length=1, max_length=100)
    new_password: str = Field(..., min_length=8, max_length=100)

    class Config:
        json_schema_extra = {
            "example": {
                "current_password": "OldPass123!",
                "new_password": "NewSecurePass456!"
            }
        }
