"""Add LLM tables for 006-llm-review-assistant

Revision ID: 20260305_llm_tables
Revises: 20260221_needs_revision
Create Date: 2026-03-05

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260305_llm_tables'
down_revision = '20260221_needs_revision'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. llm_providers 테이블 생성
    op.create_table(
        'llm_providers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('provider_name', sa.String(50), nullable=False),
        sa.Column('display_name', sa.String(100), nullable=False),
        sa.Column('model_name', sa.String(100), nullable=False),
        sa.Column('api_key_env_name', sa.String(100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('rate_limit_per_minute', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider_name', name='uq_llm_providers_name'),
    )

    # 초기 데이터 삽입
    op.execute("""
        INSERT INTO llm_providers (provider_name, display_name, model_name, api_key_env_name, is_active, rate_limit_per_minute)
        VALUES
            ('claude', 'Claude', 'claude-sonnet-4-6', 'ANTHROPIC_API_KEY', TRUE, 10),
            ('chatgpt', 'ChatGPT', 'gpt-4o', 'OPENAI_API_KEY', FALSE, 10),
            ('gemini', 'Gemini', 'gemini-2.0-flash', 'GOOGLE_AI_API_KEY', FALSE, 10)
    """)

    # 2. llm_analysis_results 테이블 생성
    op.create_table(
        'llm_analysis_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ordinance_id', sa.Integer(), nullable=False),
        sa.Column('law_id', sa.Integer(), nullable=False),
        sa.Column('law_proclaimed_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('input_hash', sa.String(64), nullable=False),
        sa.Column('prompt_text', sa.Text(), nullable=False),
        sa.Column('summary_text', sa.Text(), nullable=True),
        sa.Column('review_draft_text', sa.Text(), nullable=True),
        sa.Column('review_draft_result', sa.String(20), nullable=True),
        sa.Column('provider_name', sa.String(50), nullable=False),
        sa.Column('model_name', sa.String(100), nullable=False),
        sa.Column('token_usage', postgresql.JSONB(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['ordinance_id'], ['ordinances.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['law_id'], ['laws.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('ordinance_id', 'law_id', 'law_proclaimed_date', name='uq_llm_analysis_ord_law_date'),
    )
    op.create_index('ix_llm_analysis_ordinance', 'llm_analysis_results', ['ordinance_id'])
    op.create_index('ix_llm_analysis_law', 'llm_analysis_results', ['law_id'])
    op.create_index('ix_llm_analysis_status', 'llm_analysis_results', ['status'])

    # 3. ordinance_reviews에 AI 필드 추가
    op.add_column('ordinance_reviews', sa.Column('is_ai_generated', sa.Boolean(), server_default='false'))
    op.add_column('ordinance_reviews', sa.Column('ai_modified', sa.Boolean(), server_default='false'))
    op.add_column('ordinance_reviews', sa.Column(
        'ai_analysis_id', sa.Integer(),
        sa.ForeignKey('llm_analysis_results.id', ondelete='SET NULL'),
        nullable=True,
    ))


def downgrade() -> None:
    # 3. ordinance_reviews AI 필드 삭제
    op.drop_column('ordinance_reviews', 'ai_analysis_id')
    op.drop_column('ordinance_reviews', 'ai_modified')
    op.drop_column('ordinance_reviews', 'is_ai_generated')

    # 2. llm_analysis_results 테이블 삭제
    op.drop_index('ix_llm_analysis_status', 'llm_analysis_results')
    op.drop_index('ix_llm_analysis_law', 'llm_analysis_results')
    op.drop_index('ix_llm_analysis_ordinance', 'llm_analysis_results')
    op.drop_table('llm_analysis_results')

    # 1. llm_providers 테이블 삭제
    op.drop_table('llm_providers')
