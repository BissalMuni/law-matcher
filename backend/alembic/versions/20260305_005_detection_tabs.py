"""005: Add detection tabs tables and article fields

T006: law_revision_reasons, revision_detection_results 테이블 생성
      articles에 revision_type_detail, change_flag 추가

Revision ID: 20260305_005_tabs
Revises: 20260305_004_cleanup
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '20260305_005_tabs'
down_revision = '20260305_004_cleanup'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. law_revision_reasons 테이블 생성
    op.create_table(
        'law_revision_reasons',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('law_id', sa.Integer(), sa.ForeignKey('laws.id', ondelete='CASCADE'), unique=True, nullable=False),
        sa.Column('law_mst', sa.String(100), nullable=True),
        sa.Column('revision_reason', sa.Text(), nullable=True),
        sa.Column('amendment_content', sa.Text(), nullable=True),
        sa.Column('extracted_articles', JSONB(), nullable=True),
        sa.Column('fetched_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_law_revision_reasons_law_id', 'law_revision_reasons', ['law_id'])

    # 2. revision_detection_results 테이블 생성
    op.create_table(
        'revision_detection_results',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('ordinance_id', sa.Integer(), sa.ForeignKey('ordinances.id', ondelete='CASCADE'), nullable=False),
        sa.Column('law_id', sa.Integer(), sa.ForeignKey('laws.id', ondelete='CASCADE'), nullable=False),
        sa.Column('detection_method', sa.String(30), nullable=False),
        sa.Column('needs_revision', sa.Boolean(), nullable=False),
        sa.Column('detail', JSONB(), nullable=True),
        sa.Column('detected_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_unique_constraint(
        'uq_detection_ord_law_method',
        'revision_detection_results',
        ['ordinance_id', 'law_id', 'detection_method'],
    )
    op.create_index('ix_rdr_ordinance_id', 'revision_detection_results', ['ordinance_id'])
    op.create_index('ix_rdr_detection_method', 'revision_detection_results', ['detection_method'])

    # 3. articles 테이블에 필드 추가
    op.add_column('articles', sa.Column('revision_type_detail', sa.String(50), nullable=True))
    op.add_column('articles', sa.Column('change_flag', sa.String(5), nullable=True))


def downgrade() -> None:
    op.drop_column('articles', 'change_flag')
    op.drop_column('articles', 'revision_type_detail')
    op.drop_table('revision_detection_results')
    op.drop_table('law_revision_reasons')
