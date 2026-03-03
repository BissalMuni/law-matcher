"""Add unique constraints to articles and ordinance_article_mappings

Revision ID: 20260220_164554
Revises: update_parent_laws_dates_from_api
Create Date: 2026-02-20 16:45:54

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260220_164554'
down_revision = 'update_parent_laws_dates'
branch_labels = None
depends_on = None


def upgrade():
    # Add UNIQUE constraint to articles table: (law_id, article_no)
    op.create_unique_constraint(
        'uq_articles_law_article',
        'articles',
        ['law_id', 'article_no']
    )

    # Add UNIQUE constraint to ordinance_article_mappings table: (ordinance_id, article_id)
    op.create_unique_constraint(
        'uq_ordinance_article_mapping',
        'ordinance_article_mappings',
        ['ordinance_id', 'article_id']
    )


def downgrade():
    # Remove UNIQUE constraints
    op.drop_constraint('uq_ordinance_article_mapping', 'ordinance_article_mappings', type_='unique')
    op.drop_constraint('uq_articles_law_article', 'articles', type_='unique')
