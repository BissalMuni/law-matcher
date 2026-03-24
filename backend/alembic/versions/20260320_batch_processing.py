"""Add batch processing tables

Revision ID: batch_processing_001
Revises: None
Create Date: 2026-03-20

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'batch_processing_001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'batch_jobs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('current_step', sa.String(30), nullable=False, server_default='step1_select'),
        sa.Column('step1_status', sa.String(20), nullable=False, server_default='completed'),
        sa.Column('step2_status', sa.String(20), nullable=False, server_default='idle'),
        sa.Column('step3_status', sa.String(20), nullable=False, server_default='idle'),
        sa.Column('step4_status', sa.String(20), nullable=False, server_default='idle'),
        sa.Column('step5_status', sa.String(20), nullable=False, server_default='idle'),
        sa.Column('step2_progress', sa.Integer(), server_default='0'),
        sa.Column('step2_total', sa.Integer(), server_default='0'),
        sa.Column('step3_progress', sa.Integer(), server_default='0'),
        sa.Column('step3_total', sa.Integer(), server_default='0'),
        sa.Column('step4_progress', sa.Integer(), server_default='0'),
        sa.Column('step4_total', sa.Integer(), server_default='0'),
        sa.Column('filter_params', postgresql.JSONB(), nullable=True),
        sa.Column('summary', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('idx_batch_jobs_created_at', 'batch_jobs', ['created_at'])

    op.create_table(
        'batch_job_items',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('batch_job_id', sa.Integer(), sa.ForeignKey('batch_jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('ordinance_id', sa.Integer(), sa.ForeignKey('ordinances.id', ondelete='CASCADE'), nullable=False),
        sa.Column('ordinance_name', sa.String(500), nullable=False),
        sa.Column('ordinance_department', sa.String(200), nullable=True),
        sa.Column('ordinance_category', sa.String(100), nullable=True),
        sa.Column('step1_result', sa.String(20), nullable=False, server_default='included'),
        sa.Column('step1_reason', sa.String(200), nullable=True),
        sa.Column('step2_result', sa.String(30), nullable=True),
        sa.Column('step2_reason', sa.String(500), nullable=True),
        sa.Column('step2_detail', postgresql.JSONB(), nullable=True),
        sa.Column('step3_result', sa.String(30), nullable=True),
        sa.Column('step3_reason', sa.String(500), nullable=True),
        sa.Column('step4_result', sa.String(30), nullable=True),
        sa.Column('step4_reason', sa.String(500), nullable=True),
        sa.Column('step4_ai_summary', sa.Text(), nullable=True),
        sa.Column('step4_ai_result', sa.String(20), nullable=True),
        sa.Column('final_result', sa.String(30), nullable=True),
        sa.Column('manually_excluded', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('idx_batch_job_items_batch_id', 'batch_job_items', ['batch_job_id'])
    op.create_index(
        'idx_batch_job_items_batch_ordinance',
        'batch_job_items',
        ['batch_job_id', 'ordinance_id'],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table('batch_job_items')
    op.drop_table('batch_jobs')
