"""
API Dependencies
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import async_session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
