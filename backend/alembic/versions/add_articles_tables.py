"""add articles tables

Revision ID: add_articles_tables
Revises: add_ordinance_reviews
Create Date: 2026-02-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_articles_tables'
down_revision = 'add_review_approval_fields'
branch_labels = None
depends_on = None

# Note: This migration depends on add_review_approval_fields which is on the main branch.
# The add_law_changes branchpoint is resolved through the merge_heads_before_auth merge.


def upgrade() -> None:
    # 1. articles 테이블 생성
    op.create_table(
        'articles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('law_id', sa.Integer(), nullable=False),

        # 조문 식별
        sa.Column('article_no', sa.String(50), nullable=False),
        sa.Column('article_title', sa.String(500), nullable=True),

        # 조문 내용
        sa.Column('article_content', sa.Text(), nullable=False),
        sa.Column('paragraphs', postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        # 변경 감지용
        sa.Column('content_hash', sa.String(64), nullable=False),

        # 법제처 API 원본 정보
        sa.Column('mst_seq', sa.Integer(), nullable=True),
        sa.Column('jo_seq', sa.Integer(), nullable=True),

        # 메타데이터
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),

        sa.ForeignKeyConstraint(['law_id'], ['laws.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('law_id', 'article_no', name='uq_articles_law_id_article_no')
    )

    # articles 테이블 인덱스
    op.create_index('idx_articles_law_id', 'articles', ['law_id'])
    op.create_index('idx_articles_content_hash', 'articles', ['content_hash'])
    op.create_index('idx_articles_article_no', 'articles', ['article_no'])
    op.create_index('idx_articles_last_synced', 'articles', ['last_synced_at'])

    # 2. ordinance_article_mappings 테이블 생성
    op.create_table(
        'ordinance_article_mappings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ordinance_id', sa.Integer(), nullable=False),
        sa.Column('article_id', sa.Integer(), nullable=False),

        # 연계 정보
        sa.Column('mapping_reason', sa.Text(), nullable=True),
        sa.Column('related_article_nos', sa.String(200), nullable=True),

        # 추적 정보
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),

        sa.ForeignKeyConstraint(['ordinance_id'], ['ordinances.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ordinance_id', 'article_id', name='uq_ordinance_article_mappings')
    )

    # ordinance_article_mappings 테이블 인덱스
    op.create_index('idx_ordinance_article_mappings_ordinance_id', 'ordinance_article_mappings', ['ordinance_id'])
    op.create_index('idx_ordinance_article_mappings_article_id', 'ordinance_article_mappings', ['article_id'])

    # 3. article_changes 테이블 생성
    op.create_table(
        'article_changes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('article_id', sa.Integer(), nullable=False),

        # 변경 정보
        sa.Column('change_date', sa.Date(), nullable=False),
        sa.Column('change_type', sa.String(20), nullable=False),

        # 변경 내용
        sa.Column('old_content', sa.Text(), nullable=True),
        sa.Column('new_content', sa.Text(), nullable=True),
        sa.Column('old_hash', sa.String(64), nullable=True),
        sa.Column('new_hash', sa.String(64), nullable=True),

        # diff 정보
        sa.Column('diff_html', sa.Text(), nullable=True),

        # 감지 정보
        sa.Column('detected_at', sa.DateTime(), nullable=True),
        sa.Column('notified', sa.Boolean(), default=False),

        sa.Column('created_at', sa.DateTime(), nullable=True),

        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # article_changes 테이블 인덱스
    op.create_index('idx_article_changes_article_id', 'article_changes', ['article_id'])
    op.create_index('idx_article_changes_change_date', 'article_changes', ['change_date'])
    op.create_index('idx_article_changes_detected_at', 'article_changes', ['detected_at'])
    op.create_index('idx_article_changes_notified', 'article_changes', ['notified'])


def downgrade() -> None:
    # 역순으로 삭제
    # article_changes 인덱스 및 테이블 삭제
    op.drop_index('idx_article_changes_notified', table_name='article_changes')
    op.drop_index('idx_article_changes_detected_at', table_name='article_changes')
    op.drop_index('idx_article_changes_change_date', table_name='article_changes')
    op.drop_index('idx_article_changes_article_id', table_name='article_changes')
    op.drop_table('article_changes')

    # ordinance_article_mappings 인덱스 및 테이블 삭제
    op.drop_index('idx_ordinance_article_mappings_article_id', table_name='ordinance_article_mappings')
    op.drop_index('idx_ordinance_article_mappings_ordinance_id', table_name='ordinance_article_mappings')
    op.drop_table('ordinance_article_mappings')

    # articles 인덱스 및 테이블 삭제
    op.drop_index('idx_articles_last_synced', table_name='articles')
    op.drop_index('idx_articles_article_no', table_name='articles')
    op.drop_index('idx_articles_content_hash', table_name='articles')
    op.drop_index('idx_articles_law_id', table_name='articles')
    op.drop_table('articles')
