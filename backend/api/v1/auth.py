"""
Authentication API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db, get_current_user
from backend.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    PasswordChangeRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    MessageResponse,
)
from backend.schemas.user import UserResponse, UserWithDepartmentResponse
from backend.services.auth_service import AuthService
from backend.models.user import User
from backend.utils.email import send_password_reset_email

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user

    - **email**: User email (must be unique)
    - **username**: Username (must be unique, 3-100 characters)
    - **password**: Password (minimum 8 characters)
    - **full_name**: Full name (optional)
    - **user_type**: User type (DEPARTMENT or GENERAL)
    - **department_id**: Department ID (required for DEPARTMENT type)
    """
    service = AuthService(db)

    # Register user
    user = await service.register(
        email=data.email,
        username=data.username,
        password=data.password,
        full_name=data.full_name,
        user_type=data.user_type,
        department_id=data.department_id,
    )

    await db.commit()

    # Create access token
    access_token = service.create_token(user)

    # Build response with department info
    user_data = UserResponse.model_validate(user).model_dump()
    user_data['department_name'] = user.department.name if user.department else None
    user_data['department_code'] = user.department.code if user.department else None

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserWithDepartmentResponse(**user_data),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Login with username and password

    - **username**: Username
    - **password**: Password

    Returns JWT access token
    """
    service = AuthService(db)

    # Authenticate user
    user = await service.authenticate(data.username, data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token = service.create_token(user)

    # Build response with department info
    user_data = UserResponse.model_validate(user).model_dump()
    user_data['department_name'] = user.department.name if user.department else None
    user_data['department_code'] = user.department.code if user.department else None

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserWithDepartmentResponse(**user_data),
    )


@router.get("/me", response_model=UserWithDepartmentResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """
    Get current authenticated user information with department info

    Requires: Authorization header with Bearer token
    """
    # Build response with department info
    user_data = UserResponse.model_validate(current_user).model_dump()
    user_data['department_name'] = current_user.department.name if current_user.department else None
    user_data['department_code'] = current_user.department.code if current_user.department else None

    return UserWithDepartmentResponse(**user_data)


@router.post("/change-password", response_model=UserResponse)
async def change_password(
    data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Change current user's password

    - **current_password**: Current password (for verification)
    - **new_password**: New password (minimum 8 characters)

    Requires: Authorization header with Bearer token
    """
    service = AuthService(db)

    # Change password
    user = await service.change_password(
        user_id=current_user.id,
        current_password=data.current_password,
        new_password=data.new_password,
    )

    await db.commit()

    return UserResponse.model_validate(user)


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    data: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Request password reset email

    - **email**: User email address

    Sends a password reset link to the email if account exists.
    Always returns success to prevent email enumeration.
    """
    service = AuthService(db)

    # Create reset token
    token = await service.create_password_reset_token(data.email)

    # Send email if user exists
    if token:
        await send_password_reset_email(data.email, token)

    # Always return success to prevent email enumeration
    return MessageResponse(
        message="비밀번호 재설정 링크가 이메일로 전송되었습니다. 이메일을 확인해주세요."
    )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
):
    """
    Reset password using token

    - **token**: Password reset token from email
    - **new_password**: New password (minimum 8 characters)
    """
    service = AuthService(db)

    await service.reset_password(data.token, data.new_password)
    await db.commit()

    return MessageResponse(message="비밀번호가 성공적으로 변경되었습니다.")
