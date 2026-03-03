"""merge heads after revision detection migrations

Revision ID: 3fe6a67d9c83
Revises: add_articles_tables, 20260303_000003
Create Date: 2026-03-03 09:00:29.119794

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3fe6a67d9c83'
down_revision: Union[str, None] = ('add_articles_tables', '20260303_000003')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
