"""
Department model
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base


class Department(Base):
    """부서 정보"""
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    parent_code: Mapped[Optional[str]] = mapped_column(String(50))
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    ordinances: Mapped[List["Ordinance"]] = relationship(back_populates="department_rel")
