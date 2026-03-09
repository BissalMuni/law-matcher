"""Drop article tables (조문 기능 제거)

Revision ID: 20260307_drop_articles
Revises: 20260305_005_tabs
Create Date: 2026-03-07
"""
from alembic import op

revision = '20260307_drop_articles'
down_revision = '20260305_005_tabs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # FK 의존 순서로 삭제
    op.drop_index('idx_article_changes_notified', table_name='article_changes', if_exists=True)
    op.drop_index('idx_article_changes_detected_at', table_name='article_changes', if_exists=True)
    op.drop_index('idx_article_changes_change_date', table_name='article_changes', if_exists=True)
    op.drop_index('idx_article_changes_article_id', table_name='article_changes', if_exists=True)
    op.drop_table('article_changes')

    op.drop_index('idx_ordinance_article_mappings_article_id', table_name='ordinance_article_mappings', if_exists=True)
    op.drop_index('idx_ordinance_article_mappings_ordinance_id', table_name='ordinance_article_mappings', if_exists=True)
    op.drop_table('ordinance_article_mappings')

    op.drop_index('idx_articles_last_synced', table_name='articles', if_exists=True)
    op.drop_index('idx_articles_article_no', table_name='articles', if_exists=True)
    op.drop_index('idx_articles_content_hash', table_name='articles', if_exists=True)
    op.drop_index('idx_articles_law_id', table_name='articles', if_exists=True)
    op.drop_table('articles')


def downgrade() -> None:
    pass  # 복구 불필요
