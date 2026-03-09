"""
LLM Provider model - LLM 프로바이더/모델 DB 관리
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


class LlmProvider(Base):
    """LLM 프로바이더 관리 테이블"""
    __tablename__ = "llm_providers"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider_name: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False
    )  # 'claude' | 'chatgpt' | 'gemini'
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)  # 'Claude' | 'ChatGPT' | 'Gemini'
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)  # 'claude-sonnet-4-6' 등
    api_key_env_name: Mapped[str] = mapped_column(String(100), nullable=False)  # 'ANTHROPIC_API_KEY' 등
    api_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # DB에 저장된 API 키 (env 없을 때 fallback)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # 활성 프로바이더 (1개만 active)
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, default=10, nullable=False)

    # 타임스탬프
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<LlmProvider(id={self.id}, name={self.provider_name}, active={self.is_active})>"
