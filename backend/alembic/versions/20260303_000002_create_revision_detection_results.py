"""create revision_detection_results table

Revision ID: 20260303_000002
Revises: 20260303_000001
Create Date: 2026-03-03
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260303_000002"
down_revision = "20260303_000001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "revision_detection_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ordinance_id", sa.Integer(), nullable=False),
        sa.Column("law_id", sa.Integer(), nullable=False),
        sa.Column("detection_method", sa.String(length=30), nullable=False),
        sa.Column("needs_revision", sa.Boolean(), nullable=False),
        sa.Column("detail", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("detected_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["ordinance_id"], ["ordinances.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["law_id"], ["laws.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "ordinance_id",
            "law_id",
            "detection_method",
            name="uq_revision_detection_result",
        ),
    )
    op.create_index(
        "idx_revision_detection_results_ordinance_id",
        "revision_detection_results",
        ["ordinance_id"],
        unique=False,
    )
    op.create_index(
        "idx_revision_detection_results_detection_method",
        "revision_detection_results",
        ["detection_method"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        "idx_revision_detection_results_detection_method",
        table_name="revision_detection_results",
    )
    op.drop_index(
        "idx_revision_detection_results_ordinance_id",
        table_name="revision_detection_results",
    )
    op.drop_table("revision_detection_results")
