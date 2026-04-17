"""add sync_settings table (merge heads)

Revision ID: 20260417_sync
Revises: batch_processing_001, 20260406_002
Create Date: 2026-04-17
"""
from alembic import op
import sqlalchemy as sa


revision = "20260417_sync"
down_revision = ("batch_processing_001", "20260406_002")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sync_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("auto_sync_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("interval_hours", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("last_sync_at", sa.DateTime(), nullable=True),
        sa.Column("next_sync_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        "INSERT INTO sync_settings (id, auto_sync_enabled, interval_hours) "
        "VALUES (1, false, 24)"
    )


def downgrade() -> None:
    op.drop_table("sync_settings")
