"""merge heads before auth implementation

Revision ID: merge_heads_before_auth
Revises: cc3557cac770, drop_ordinance_articles, add_ordinance_reviews
Create Date: 2024-02-04 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'merge_heads_before_auth'
down_revision = ('cc3557cac770', 'drop_ordinance_articles', 'add_ordinance_reviews')
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This is a merge migration, no changes needed
    pass


def downgrade() -> None:
    # This is a merge migration, no changes needed
    pass
