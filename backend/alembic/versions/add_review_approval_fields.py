"""add review approval fields

ordinance_reviews 테이블에 approval_status, approved_by_id, approved_at, approval_note 필드 추가

Revision ID: add_review_approval_fields
Revises: add_department_fields
Create Date: 2025-01-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "add_review_approval_fields"
down_revision: Union[str, None] = "add_department_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add approval fields to ordinance_reviews
    op.add_column(
        "ordinance_reviews",
        sa.Column("approval_status", sa.String(20), nullable=True, server_default="pending")
    )
    op.add_column(
        "ordinance_reviews",
        sa.Column("approved_by_id", sa.Integer(), nullable=True)
    )
    op.add_column(
        "ordinance_reviews",
        sa.Column("approved_at", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "ordinance_reviews",
        sa.Column("approval_note", sa.Text(), nullable=True)
    )

    # Add foreign key constraint for approved_by_id
    op.create_foreign_key(
        "fk_ordinance_reviews_approved_by_id",
        "ordinance_reviews", "users",
        ["approved_by_id"], ["id"],
        ondelete="SET NULL"
    )


def downgrade() -> None:
    # Drop foreign key constraint
    op.drop_constraint("fk_ordinance_reviews_approved_by_id", "ordinance_reviews", type_="foreignkey")

    # Drop columns
    op.drop_column("ordinance_reviews", "approval_note")
    op.drop_column("ordinance_reviews", "approved_at")
    op.drop_column("ordinance_reviews", "approved_by_id")
    op.drop_column("ordinance_reviews", "approval_status")
