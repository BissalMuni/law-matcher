"""Add ordinance_texts table and affected_articles_json to llm_analysis_results

Revision ID: 20260310_ordin_text
Revises: 6de02d3fbf80
Create Date: 2026-03-10
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '20260310_ordin_text'
down_revision = '6de02d3fbf80'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. ordinance_texts 테이블 생성
    op.create_table(
        'ordinance_texts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('ordinance_id', sa.Integer(), sa.ForeignKey('ordinances.id', ondelete='CASCADE'), nullable=False),
        sa.Column('serial_no', sa.String(50), nullable=False),
        sa.Column('full_text', sa.Text(), nullable=True),
        sa.Column('articles_json', JSONB(), nullable=True),
        sa.Column('fetched_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint('ordinance_id', name='uq_ordinance_texts_ordinance_id'),
    )
    op.create_index('idx_ordinance_texts_fetched_at', 'ordinance_texts', ['fetched_at'])

    # 2. llm_analysis_results에 affected_articles_json 컬럼 추가
    op.add_column('llm_analysis_results', sa.Column('affected_articles_json', JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column('llm_analysis_results', 'affected_articles_json')
    op.drop_index('idx_ordinance_texts_fetched_at', 'ordinance_texts')
    op.drop_table('ordinance_texts')
