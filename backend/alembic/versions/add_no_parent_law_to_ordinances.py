"""add no_parent_law to ordinances

ordinances 테이블에 no_parent_law 컬럼 추가
- 상위법령이 없음을 확인한 조례를 표시하는 플래그

Revision ID: add_no_parent_law
Revises: add_law_changes
Create Date: 2025-01-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_no_parent_law'
down_revision: Union[str, None] = 'add_law_changes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'ordinances',
        sa.Column('no_parent_law', sa.Boolean(), nullable=False, server_default='false')
    )


def downgrade() -> None:
    op.drop_column('ordinances', 'no_parent_law')
