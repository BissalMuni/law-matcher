"""change dept_code columns from Integer to String

Revision ID: 20260406_002
Revises: 20260406_001
Create Date: 2026-04-06
"""
import sqlalchemy as sa
from alembic import op


revision = "20260406_002"
down_revision = "20260406_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "laws", "dept_code",
        existing_type=sa.Integer(),
        type_=sa.String(200),
        existing_nullable=True,
        postgresql_using="dept_code::text",
    )
    op.alter_column(
        "law_changes", "dept_code",
        existing_type=sa.Integer(),
        type_=sa.String(200),
        existing_nullable=True,
        postgresql_using="dept_code::text",
    )


def downgrade() -> None:
    op.alter_column(
        "laws", "dept_code",
        existing_type=sa.String(200),
        type_=sa.Integer(),
        existing_nullable=True,
        postgresql_using="dept_code::integer",
    )
    op.alter_column(
        "law_changes", "dept_code",
        existing_type=sa.String(200),
        type_=sa.Integer(),
        existing_nullable=True,
        postgresql_using="dept_code::integer",
    )
