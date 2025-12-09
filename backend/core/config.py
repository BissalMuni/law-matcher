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

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
