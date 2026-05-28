"""create drafting (입안심사) tables — law-ebansimsa 통합

신규 테이블만 추가하는 additive 마이그레이션. 기존 테이블 변경 없음.
ordinances 테이블은 FK 참조만 한다.

Revision ID: 20260527_drafting
Revises: 20260417_sync
Create Date: 2026-05-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260527_drafting"
down_revision = "20260417_sync"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # drafting_projects
    op.create_table(
        "drafting_projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ordinance_id", sa.Integer(), nullable=True),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("municipality", sa.String(length=200), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("locked_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["ordinance_id"], ["ordinances.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_drafting_projects_ordinance_id", "drafting_projects", ["ordinance_id"])
    op.create_index("ix_drafting_projects_status", "drafting_projects", ["status"])

    # drafting_stages (self-FK parent_id)
    op.create_table(
        "drafting_stages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=50), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column("stale_reason", sa.Text(), nullable=True),
        sa.Column("wiki_ref", sa.String(length=50), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["drafting_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["drafting_stages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "key", "parent_id", name="uq_drafting_stage_key"),
    )
    op.create_index("ix_drafting_stages_project_id", "drafting_stages", ["project_id"])
    op.create_index(
        "idx_drafting_stages_project_order", "drafting_stages", ["project_id", "sort_order"]
    )

    # drafting_sections
    op.create_table(
        "drafting_sections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("stage_id", sa.Integer(), nullable=False),
        sa.Column("article_no", sa.Integer(), nullable=False),
        sa.Column("article_label", sa.String(length=200), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("original_body", sa.Text(), nullable=True),
        sa.Column("change_type", sa.String(length=20), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["drafting_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["stage_id"], ["drafting_stages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_drafting_sections_project_id", "drafting_sections", ["project_id"])
    op.create_index("ix_drafting_sections_stage_id", "drafting_sections", ["stage_id"])
    op.create_index(
        "idx_drafting_sections_project_order", "drafting_sections", ["project_id", "sort_order"]
    )

    # drafting_messages
    op.create_table(
        "drafting_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stage_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("attachments", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("applied", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["stage_id"], ["drafting_stages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_drafting_messages_stage_id", "drafting_messages", ["stage_id"])
    op.create_index(
        "idx_drafting_messages_stage_created", "drafting_messages", ["stage_id", "created_at"]
    )

    # drafting_validations
    op.create_table(
        "drafting_validations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("section_id", sa.Integer(), nullable=False),
        sa.Column("criterion_id", sa.String(length=50), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("verdict", sa.String(length=20), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("suggestion", sa.Text(), nullable=True),
        sa.Column("dismissed_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["section_id"], ["drafting_sections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_drafting_validations_section_id", "drafting_validations", ["section_id"])
    op.create_index(
        "idx_drafting_validations_section_verdict",
        "drafting_validations",
        ["section_id", "verdict"],
    )

    # drafting_references
    op.create_table(
        "drafting_references",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("ordinance_id", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("municipality", sa.String(length=200), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("included_in_context", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["drafting_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ordinance_id"], ["ordinances.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_drafting_references_project_id", "drafting_references", ["project_id"])
    op.create_index("idx_drafting_references_project", "drafting_references", ["project_id"])

    # drafting_snapshots
    op.create_table(
        "drafting_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stage_id", sa.Integer(), nullable=False),
        sa.Column("trigger_type", sa.String(length=20), nullable=False),
        sa.Column("actor", sa.String(length=20), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=True),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["stage_id"], ["drafting_stages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_drafting_snapshots_stage_id", "drafting_snapshots", ["stage_id"])
    op.create_index(
        "idx_drafting_snapshots_stage_created", "drafting_snapshots", ["stage_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_table("drafting_snapshots")
    op.drop_table("drafting_references")
    op.drop_table("drafting_validations")
    op.drop_table("drafting_messages")
    op.drop_table("drafting_sections")
    op.drop_table("drafting_stages")
    op.drop_table("drafting_projects")
