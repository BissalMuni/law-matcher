"""
Authentication API endpoints
Database-based user authentication
"""
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.core.security import create_access_token, decode_access_token, verify_password
from backend.api.deps import get_db
from backend.models.user import User

security = HTTPBearer()

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str
    department_name: str | None = None  # 부서 로그인 시 부서명


class SimpleUser(BaseModel):
    id: int
    username: str
    user_type: str  # "ADMIN" or "USER"
    full_name: str
    department_name: str | None = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: SimpleUser


@router.post("/login", response_model=LoginResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Database-based user authentication

    - username: 사용자명 또는 부서명
    - password: 비밀번호
    """
    # Find user by username
    result = await db.execute(
        select(User)
        .options(selectinload(User.department))
        .where(User.username == data.username)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="아이디 또는 비밀번호가 올바르지 않습니다",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다",
        )

    # Determine user type for frontend
    is_admin = user.user_type == "GENERAL"  # GENERAL = 관리자
    frontend_user_type = "ADMIN" if is_admin else "USER"

    # Get department name
    dept_name = data.department_name
    if user.department:
        dept_name = user.department.name

    # Create user object for response
    response_user = SimpleUser(
        id=user.id,
        username=user.username,
        user_type=frontend_user_type,
        full_name=user.full_name or user.username,
        department_name=dept_name,
    )

    # Create access token
    token_data = {
        "sub": str(user.id),
        "username": user.username,
        "user_type": frontend_user_type,
        "department_name": dept_name,
    }
    access_token = create_access_token(token_data)

    return LoginResponse(
        access_token=access_token,
        user=response_user,
    )


@router.get("/me", response_model=SimpleUser)
async def get_current_user_info(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Get current user info from JWT token
    """
    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 토큰입니다",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return SimpleUser(
        id=int(payload.get("sub", 0)),
        username=payload.get("username", ""),
        user_type=payload.get("user_type", "USER"),
        full_name="관리자" if payload.get("user_type") == "ADMIN" else payload.get("username", ""),
        department_name=payload.get("department_name"),
    )
