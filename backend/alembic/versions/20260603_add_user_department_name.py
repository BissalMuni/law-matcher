"""add department_name to users (모델↔스키마 불일치 보정)

User 모델에는 department_name 이 있으나 이를 추가하는 마이그레이션이 없어
users 조회(로그인 포함)가 UndefinedColumnError 로 깨지던 문제를 바로잡는다.

Revision ID: 20260603_userdeptname
Revises: 20260527_mapcrit
Create Date: 2026-06-03
"""
from alembic import op
import sqlalchemy as sa


revision = "20260603_userdeptname"
down_revision = "20260527_mapcrit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("department_name", sa.String(length=200), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "department_name")
