"""
API Dependencies
"""
from typing import AsyncGenerator
from fastapi import Header, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import async_session
from backend.core.config import settings
from backend.core.security import decode_access_token
from backend.models.user import User


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def verify_admin_password(x_admin_password: str = Header(..., description="관리자 비밀번호")) -> bool:
    """
    관리자 비밀번호 검증

    Headers에 X-Admin-Password를 통해 비밀번호 전달
    """
    if x_admin_password != settings.ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 비밀번호가 올바르지 않습니다."
        )
    return True


# JWT Bearer security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get current authenticated user from JWT token

    Args:
        credentials: HTTP Bearer credentials (JWT token)
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials

    # Decode and verify token
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user_id from token payload
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database with department info
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(User)
        .options(selectinload(User.department))
        .where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        # 간단한 로그인(auth.py)에서 생성된 토큰인 경우 가상 사용자 생성
        username = payload.get("username", "")
        user_type = payload.get("user_type", "USER")

        # 가상 사용자 생성 (DB에 저장하지 않음)
        user = User(
            id=user_id,
            username=username,
            full_name="관리자" if user_type == "ADMIN" else username,
            user_type="GENERAL" if user_type == "ADMIN" else "DEPARTMENT",
            is_active=True,
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    return user
