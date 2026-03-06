"""004: revision_status 도입, law_changes 단순화, review_result 정리

Revision ID: 20260305_004_cleanup
Revises: 20260305_llm_tables
Create Date: 2026-03-05

T001: ordinances.needs_revision → revision_status 전환
T002: law_changes에서 승인/반려 관련 컬럼 제거
T003: ordinance_reviews.review_result 기존 '검토중' 값 정리
"""
from alembic import op
import sqlalchemy as sa

revision = '20260305_004_cleanup'
down_revision = '20260305_llm_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # === T001: ordinances.revision_status 도입 ===
    # 1. revision_status 컬럼 추가
    op.add_column('ordinances', sa.Column('revision_status', sa.String(20), nullable=True))
    op.create_index('ix_ordinances_revision_status', 'ordinances', ['revision_status'])

    # 2. 기존 데이터 이관: needs_revision=True → "검토대기"
    op.execute("UPDATE ordinances SET revision_status = '검토대기' WHERE needs_revision = TRUE")

    # 3. needs_revision 컬럼 제거
    op.drop_column('ordinances', 'needs_revision')

    # === T002: law_changes 단순화 ===
    # 승인/반려 관련 컬럼 제거
    op.drop_index('ix_law_changes_status', table_name='law_changes', if_exists=True)
    op.drop_column('law_changes', 'status')
    op.drop_column('law_changes', 'processed_at')
    op.drop_column('law_changes', 'processed_by')
    op.drop_column('law_changes', 'process_note')
    op.drop_column('law_changes', 'updated_at')

    # UNIQUE(law_id, sync_batch_id) 제약 추가
    op.create_unique_constraint(
        'uq_law_changes_law_batch',
        'law_changes',
        ['law_id', 'sync_batch_id']
    )

    # === T003: ordinance_reviews.review_result 정리 ===
    # '검토중' → '개정필요' 로 변환 (기존 데이터 정리)
    op.execute("UPDATE ordinance_reviews SET review_result = '개정필요' WHERE review_result = '검토중'")
    # '보류' 데이터가 있으면 '개정불필요'로 변환
    op.execute("UPDATE ordinance_reviews SET review_result = '개정불필요' WHERE review_result = '보류'")


def downgrade() -> None:
    # === T003 rollback ===
    # 데이터 변환은 원복 불가 (단방향)

    # === T002 rollback ===
    op.drop_constraint('uq_law_changes_law_batch', 'law_changes', type_='unique')
    op.add_column('law_changes', sa.Column('status', sa.String(20), nullable=True, server_default='pending'))
    op.add_column('law_changes', sa.Column('processed_at', sa.DateTime, nullable=True))
    op.add_column('law_changes', sa.Column('processed_by', sa.String(100), nullable=True))
    op.add_column('law_changes', sa.Column('process_note', sa.Text, nullable=True))
    op.add_column('law_changes', sa.Column('updated_at', sa.DateTime, nullable=True))
    op.create_index('ix_law_changes_status', 'law_changes', ['status'])

    # === T001 rollback ===
    op.add_column('ordinances', sa.Column('needs_revision', sa.Boolean, nullable=True))
    op.execute("UPDATE ordinances SET needs_revision = TRUE WHERE revision_status IS NOT NULL")
    op.drop_index('ix_ordinances_revision_status', table_name='ordinances')
    op.drop_column('ordinances', 'revision_status')
