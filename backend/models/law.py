"""
Law (상위법령) master model
Based on 법제처 현행법령 API response fields
"""
from datetime import datetime, date
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Text, Date, DateTime, Integer, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base

if TYPE_CHECKING:
    from backend.models.ordinance_law_mapping import OrdinanceLawMapping


class Law(Base):
    """
    상위법령 마스터 테이블

    법제처 현행법령 API (target=law) 응답 필드 기반
    http://www.law.go.kr/DRF/lawSearch.do?target=law
    """
    __tablename__ = "laws"

    id: Mapped[int] = mapped_column(primary_key=True)

    # 법령 식별자
    law_serial_no: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)  # 법령일련번호
    law_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)  # 법령ID

    # 법령 기본 정보
    law_name: Mapped[str] = mapped_column(String(500), nullable=False)  # 법령명한글
    law_abbr: Mapped[Optional[str]] = mapped_column(String(200))  # 법령약칭명
    law_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 법령구분명 (법률/대통령령/총리령/부령)

    # 공포/시행 정보
    proclaimed_date: Mapped[Optional[date]] = mapped_column(Date, index=True)  # 공포일자 - 개정 감지용
    proclaimed_no: Mapped[Optional[int]] = mapped_column(Integer)  # 공포번호
    enforced_date: Mapped[Optional[date]] = mapped_column(Date)  # 시행일자

    # 제개정 정보
    revision_type: Mapped[Optional[str]] = mapped_column(String(50))  # 제개정구분명 (제정/일부개정/전부개정 등)
    history_code: Mapped[Optional[str]] = mapped_column(String(20))  # 현행연혁코드

    # 소관부처 정보
    dept_name: Mapped[Optional[str]] = mapped_column(String(200))  # 소관부처명
    dept_code: Mapped[Optional[int]] = mapped_column(Integer)  # 소관부처코드

    # 공동부령 정보
    joint_dept_info: Mapped[Optional[str]] = mapped_column(String(50))  # 공동부령구분
    joint_proclaimed_no: Mapped[Optional[str]] = mapped_column(String(100))  # 공동부령 공포번호

    # 기타 정보
    self_other_law: Mapped[Optional[str]] = mapped_column(String(20))  # 자법타법여부
    detail_link: Mapped[Optional[str]] = mapped_column(String(500))  # 법령상세링크

    # 동기화 관리
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime)  # 마지막 API 동기화 시점
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    ordinance_mappings: Mapped[List["OrdinanceLawMapping"]] = relationship(
        back_populates="law", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Law(id={self.id}, name={self.law_name}, type={self.law_type})>"
