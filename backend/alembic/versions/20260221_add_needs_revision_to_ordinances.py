"""Add needs_revision column to ordinances

Revision ID: 20260221_needs_revision
Revises: 20260220_164554
Create Date: 2026-02-21

"""
from alembic import op
import sqlalchemy as sa


revision = '20260221_needs_revision'
down_revision = '20260220_164554'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'ordinances',
        sa.Column('needs_revision', sa.Boolean(), nullable=True)
    )


def downgrade():
    op.drop_column('ordinances', 'needs_revision')
