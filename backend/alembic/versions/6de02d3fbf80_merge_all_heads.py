"""merge all heads

Revision ID: 6de02d3fbf80
Revises: 20260308_add_unique_law_id, 20260309_llm_api_key, 3fe6a67d9c83
Create Date: 2026-03-09 13:19:38.058766

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6de02d3fbf80'
down_revision: Union[str, None] = ('20260308_add_unique_law_id', '20260309_llm_api_key', '3fe6a67d9c83')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
