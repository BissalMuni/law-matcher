"""add moleg fields to ordinances

Revision ID: add_moleg_fields
Revises: 51d1c06346dc
Create Date: 2025-12-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_moleg_fields'
down_revision: Union[str, None] = '51d1c06346dc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 법제처 API 추가 필드
    op.add_column('ordinances', sa.Column('serial_no', sa.String(length=50), nullable=True))
    op.add_column('ordinances', sa.Column('field_name', sa.String(length=200), nullable=True))
    op.add_column('ordinances', sa.Column('org_name', sa.String(length=200), nullable=True))
    op.add_column('ordinances', sa.Column('promulgation_no', sa.String(length=50), nullable=True))
    op.add_column('ordinances', sa.Column('revision_type', sa.String(length=50), nullable=True))
    op.add_column('ordinances', sa.Column('detail_link', sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column('ordinances', 'detail_link')
    op.drop_column('ordinances', 'revision_type')
    op.drop_column('ordinances', 'promulgation_no')
    op.drop_column('ordinances', 'org_name')
    op.drop_column('ordinances', 'field_name')
    op.drop_column('ordinances', 'serial_no')
