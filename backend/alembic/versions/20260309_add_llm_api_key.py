"""Add api_key column to llm_providers for DB-based key storage

Revision ID: 20260309_llm_api_key
Revises: 20260305_llm_tables
Create Date: 2026-03-09

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260309_llm_api_key'
down_revision = '20260305_llm_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('llm_providers', sa.Column('api_key', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('llm_providers', 'api_key')
