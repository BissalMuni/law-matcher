"""
Application configuration using Pydantic Settings
"""
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Project
    PROJECT_NAME: str = "Law Matcher"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/lawmatcher"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # MOLEG API (법제처)
    MOLEG_API_KEY: str = ""
    MOLEG_API_BASE_URL: str = "https://www.law.go.kr/DRF"

    # Login passwords (set via environment variables)
    ADMIN_PASSWORD: str = "admin123"  # 관리자 비밀번호
    USER_PASSWORD: str = "user123"    # 일반 사용자 비밀번호

    # JWT Authentication
    SECRET_KEY: str = "your-secret-key-change-this-in-production-min-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30  # 30 minutes

    # Email (SMTP)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "자치법규 정비 시스템"

    # Frontend URL (for password reset link)
    FRONTEND_URL: str = "http://localhost:5173"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    class Config:
        env_file = "../.env"  # 루트/.env 사용
        case_sensitive = True
        extra = "ignore"  # VITE_ 등 정의되지 않은 변수 무시


settings = Settings()
