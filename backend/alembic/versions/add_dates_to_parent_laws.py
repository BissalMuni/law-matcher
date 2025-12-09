"""add dates to parent_laws

Revision ID: add_dates_to_parent_laws
Revises: add_moleg_fields_to_ordinances
Create Date: 2025-12-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_dates_to_parent_laws'
down_revision: Union[str, None] = 'add_moleg_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # parent_laws 테이블에 날짜 필드 추가
    op.add_column('parent_laws', sa.Column('proclaimed_date', sa.Date(), nullable=True))
    op.add_column('parent_laws', sa.Column('enforced_date', sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column('parent_laws', 'enforced_date')
    op.drop_column('parent_laws', 'proclaimed_date')
