"""
Authentication Service
"""
import secrets
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
import redis.asyncio as redis

from backend.models.user import User
from backend.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
)
from backend.core.exceptions import NotFoundError
from backend.core.config import settings


class AuthService:
    """Authentication business logic"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username with department info"""
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.department))
            .where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def authenticate(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate user with username and password

        Args:
            username: Username
            password: Plain text password

        Returns:
            User object if authentication successful, None otherwise
        """
        user = await self.get_by_username(username)
        if not user:
            return None

        if not verify_password(password, user.hashed_password):
            return None

        if not user.is_active:
            return None

        return user

    async def register(
        self,
        email: str,
        username: str,
        password: str,
        full_name: Optional[str] = None,
        user_type: str = "GENERAL",
        department_id: Optional[int] = None,
    ) -> User:
        """
        Register a new user

        Args:
            email: User email
            username: Username
            password: Plain text password
            full_name: Full name (optional)
            user_type: User type (DEPARTMENT or GENERAL)
            department_id: Department ID (optional, required for DEPARTMENT type)

        Returns:
            Created user object

        Raises:
            HTTPException: If username or email already exists
        """
        # Check if username exists
        existing_user = await self.get_by_username(username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )

        # Check if email exists
        existing_email = await self.get_by_email(email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Validate department_id for DEPARTMENT type
        if user_type == "DEPARTMENT" and not department_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="department_id is required for DEPARTMENT user type"
            )

        # Create user
        hashed_password = get_password_hash(password)
        user = User(
            email=email,
            username=username,
            hashed_password=hashed_password,
            full_name=full_name,
            user_type=user_type,
            department_id=department_id,
            is_active=True,
        )

        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)

        return user

    async def change_password(
        self,
        user_id: int,
        current_password: str,
        new_password: str,
    ) -> User:
        """
        Change user password

        Args:
            user_id: User ID
            current_password: Current password (for verification)
            new_password: New password

        Returns:
            Updated user object

        Raises:
            HTTPException: If current password is incorrect
            NotFoundError: If user not found
        """
        user = await self.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")

        # Verify current password
        if not verify_password(current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )

        # Update password
        user.hashed_password = get_password_hash(new_password)
        await self.db.flush()
        await self.db.refresh(user)

        return user

    def create_token(self, user: User) -> str:
        """
        Create JWT access token for user

        Args:
            user: User object

        Returns:
            JWT access token
        """
        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "user_type": user.user_type,
        }
        return create_access_token(token_data)

    async def create_password_reset_token(self, email: str) -> Optional[str]:
        """
        Create password reset token and store in Redis

        Args:
            email: User email

        Returns:
            Reset token if user exists, None otherwise
        """
        user = await self.get_by_email(email)
        if not user:
            return None

        # Generate secure token
        token = secrets.token_urlsafe(32)

        # Store token in Redis with expiration
        redis_client = redis.from_url(settings.REDIS_URL)
        try:
            key = f"password_reset:{token}"
            await redis_client.setex(
                key,
                settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES * 60,
                str(user.id)
            )
        finally:
            await redis_client.close()

        return token

    async def verify_password_reset_token(self, token: str) -> Optional[int]:
        """
        Verify password reset token

        Args:
            token: Reset token

        Returns:
            User ID if token is valid, None otherwise
        """
        redis_client = redis.from_url(settings.REDIS_URL)
        try:
            key = f"password_reset:{token}"
            user_id = await redis_client.get(key)
            if user_id:
                return int(user_id)
            return None
        finally:
            await redis_client.close()

    async def reset_password(self, token: str, new_password: str) -> User:
        """
        Reset user password using token

        Args:
            token: Password reset token
            new_password: New password

        Returns:
            Updated user object

        Raises:
            HTTPException: If token is invalid or expired
        """
        user_id = await self.verify_password_reset_token(token)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="유효하지 않거나 만료된 토큰입니다"
            )

        user = await self.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="사용자를 찾을 수 없습니다"
            )

        # Update password
        user.hashed_password = get_password_hash(new_password)
        await self.db.flush()
        await self.db.refresh(user)

        # Delete used token from Redis
        redis_client = redis.from_url(settings.REDIS_URL)
        try:
            await redis_client.delete(f"password_reset:{token}")
        finally:
            await redis_client.close()

        return user
