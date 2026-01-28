"""drop ordinance_articles table

미사용 테이블 ordinance_articles 삭제

Revision ID: drop_ordinance_articles
Revises: add_no_parent_law
Create Date: 2025-01-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "drop_ordinance_articles"
down_revision: Union[str, None] = "add_no_parent_law"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("ordinance_articles")


def downgrade() -> None:
    op.create_table(
        "ordinance_articles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ordinance_id", sa.Integer(), sa.ForeignKey("ordinances.id"), nullable=False),
        sa.Column("article_no", sa.String(20), nullable=False),
        sa.Column("paragraph_no", sa.String(20), nullable=True),
        sa.Column("item_no", sa.String(20), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
