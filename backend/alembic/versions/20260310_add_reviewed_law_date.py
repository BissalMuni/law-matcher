"""add reviewed_law_date to ordinance_law_mappings

Revision ID: 20260310_reviewed
Revises: 20260310_ordin_text
Create Date: 2026-03-10
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '20260310_reviewed'
down_revision: Union[str, None] = '20260310_ordin_text'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'ordinance_law_mappings',
        sa.Column('reviewed_law_date', sa.Date(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('ordinance_law_mappings', 'reviewed_law_date')
