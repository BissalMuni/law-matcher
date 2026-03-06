"""
LLM Analysis Result model - AI 통합 분석 결과
"""
from datetime import datetime, date
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, Date, DateTime, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base

if TYPE_CHECKING:
    from backend.models.ordinance import Ordinance
    from backend.models.law import Law


class LlmAnalysisResult(Base):
    """AI 통합 분석 결과 테이블 - 1회 호출로 요약+초안 동시 저장"""
    __tablename__ = "llm_analysis_results"
    __table_args__ = (
        UniqueConstraint(
            "ordinance_id", "law_id", "law_proclaimed_date",
            name="uq_llm_analysis_ord_law_date"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ordinance_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ordinances.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    law_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("laws.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    law_proclaimed_date: Mapped[Optional[date]] = mapped_column(Date)  # 법령 버전 구분 (FR-005a)

    # 분석 상태
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False, index=True
    )  # 'pending' | 'success' | 'failed'

    # 입력 데이터 해시 (제개정이유 + 개정문 + 조례 텍스트)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # LLM 입출력 보존 (Constitution I. 데이터 무결성)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)  # LLM에 전송한 전체 프롬프트

    # AI 분석 결과
    summary_text: Mapped[Optional[str]] = mapped_column(Text)  # AI 개정내용 요약
    review_draft_text: Mapped[Optional[str]] = mapped_column(Text)  # AI 검토의견 초안 내용
    review_draft_result: Mapped[Optional[str]] = mapped_column(String(20))  # '개정필요' | '개정불필요'

    # 프로바이더/모델 정보
    provider_name: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    token_usage: Mapped[Optional[dict]] = mapped_column(JSONB)  # {"input_tokens": N, "output_tokens": M}

    # 에러 정보
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    # 타임스탬프
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    ordinance: Mapped["Ordinance"] = relationship()
    law: Mapped["Law"] = relationship()

    def __repr__(self) -> str:
        return f"<LlmAnalysisResult(id={self.id}, ord={self.ordinance_id}, law={self.law_id}, status={self.status})>"
