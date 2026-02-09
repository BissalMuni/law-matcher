"""add department fields

departments 테이블에 sort_order, manager_name, department_type 필드 추가

Revision ID: add_department_fields
Revises: drop_ordinance_articles
Create Date: 2025-01-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "add_department_fields"
down_revision: Union[str, None] = "add_user_tracking_to_reviews"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("departments", sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("departments", sa.Column("parent_name", sa.String(200), nullable=True))
    op.drop_column("departments", "phone")
    op.drop_column("departments", "parent_code")


def downgrade() -> None:
    op.add_column("departments", sa.Column("parent_code", sa.String(50), nullable=True))
    op.add_column("departments", sa.Column("phone", sa.String(50), nullable=True))
    op.drop_column("departments", "parent_name")
    op.drop_column("departments", "sort_order")
