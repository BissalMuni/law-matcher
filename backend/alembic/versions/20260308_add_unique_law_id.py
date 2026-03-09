"""add unique constraint on laws.law_id

Revision ID: 20260308_add_unique_law_id
Revises: 20260307_drop_articles
Create Date: 2026-03-08
"""
from alembic import op

revision = '20260308_add_unique_law_id'
down_revision = '20260307_drop_articles'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # laws.law_id에 unique 제약 추가 (법령당 최신 개정본 1건만 유지)
    op.create_unique_constraint('uq_laws_law_id', 'laws', ['law_id'])


def downgrade() -> None:
    op.drop_constraint('uq_laws_law_id', 'laws', type_='unique')
