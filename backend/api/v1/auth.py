"""
Authentication API endpoints
Database-based user authentication
"""
import logging
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.core.security import create_access_token, decode_access_token, verify_password, get_password_hash
from backend.api.deps import get_db, get_current_user
from backend.models.user import User
from backend.schemas.auth import PasswordChangeRequest

logger = logging.getLogger(__name__)

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
    department_id: int | None = None
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
    if not data.username or not data.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="아이디와 비밀번호를 모두 입력하세요.",
        )

    try:
        result = await db.execute(
            select(User)
            .options(selectinload(User.department))
            .where(User.username == data.username)
        )
        user = result.scalar_one_or_none()
    except Exception:
        logger.exception("로그인 처리 중 DB 오류")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서버 오류가 발생했습니다. 잠시 후 다시 시도하세요.",
        )

    if not user or not verify_password(data.password, user.hashed_password):
        logger.info("로그인 실패: username=%s", data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="아이디 또는 비밀번호가 올바르지 않습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다. 관리자에게 문의하세요.",
        )

    # Determine user type for frontend
    is_admin = user.user_type == "ADMIN"
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
        department_id=user.department_id,
        department_name=dept_name,
    )

    # Create access token
    token_data = {
        "sub": str(user.id),
        "username": user.username,
        "user_type": frontend_user_type,
        "department_id": user.department_id,
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
        department_id=payload.get("department_id"),
        department_name=payload.get("department_name"),
    )


@router.put("/change-password")
async def change_password(
    data: PasswordChangeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """비밀번호 변경 (인증 필요)"""
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="현재 비밀번호가 일치하지 않습니다.",
        )

    current_user.hashed_password = get_password_hash(data.new_password)
    await db.commit()
    return {"message": "비밀번호가 변경되었습니다."}
