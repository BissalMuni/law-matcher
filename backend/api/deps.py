"""
API Dependencies
"""
from typing import AsyncGenerator
from fastapi import Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import async_session
from backend.core.config import settings


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
