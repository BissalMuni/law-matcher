"""add ordinance_reviews table

Revision ID: add_ordinance_reviews
Revises: add_law_changes_table
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_ordinance_reviews'
# 기존에 주석으로 적혀 있던 것처럼 이전 리비전은 add_law_changes 를 따라야 한다.
# 그래야 ordinances 관련 테이블이 먼저 생성된 뒤 본 migration 이 실행된다.
down_revision = 'add_law_changes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'ordinance_reviews',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ordinance_id', sa.Integer(), nullable=False),
        sa.Column('reviewer_type', sa.String(50), nullable=False),
        sa.Column('reviewer_name', sa.String(100), nullable=True),
        sa.Column('reviewer_department', sa.String(200), nullable=True),
        sa.Column('review_content', sa.Text(), nullable=False),
        sa.Column('review_result', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['ordinance_id'], ['ordinances.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ordinance_reviews_ordinance_id', 'ordinance_reviews', ['ordinance_id'])


def downgrade() -> None:
    op.drop_index('ix_ordinance_reviews_ordinance_id', table_name='ordinance_reviews')
    op.drop_table('ordinance_reviews')
