"""add law_changes table

법령 변경 이력을 관리하는 테이블 추가
- 동기화 시 감지된 변경사항 저장
- 부서별 관리 및 승인 워크플로우 지원

Revision ID: add_law_changes
Revises: restructure_laws
Create Date: 2025-01-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_law_changes'
down_revision: Union[str, None] = 'restructure_laws'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'law_changes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('law_id', sa.Integer(), nullable=False),
        sa.Column('sync_date', sa.DateTime(), nullable=False),
        sa.Column('sync_batch_id', sa.String(length=50), nullable=True),
        sa.Column('api_status', sa.Enum('success', 'no_response', 'not_found', name='apistatus'), nullable=False),
        sa.Column('api_message', sa.String(length=500), nullable=True),
        sa.Column('old_values', sa.JSON(), nullable=True),
        sa.Column('new_values', sa.JSON(), nullable=True),
        sa.Column('dept_name', sa.String(length=200), nullable=True),
        sa.Column('dept_code', sa.Integer(), nullable=True),
        sa.Column('status', sa.Enum('pending', 'reviewing', 'approved', 'rejected', name='changestatus'), nullable=False),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('processed_by', sa.String(length=100), nullable=True),
        sa.Column('process_note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['law_id'], ['laws.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_law_changes_law_id'), 'law_changes', ['law_id'], unique=False)
    op.create_index(op.f('ix_law_changes_sync_date'), 'law_changes', ['sync_date'], unique=False)
    op.create_index(op.f('ix_law_changes_sync_batch_id'), 'law_changes', ['sync_batch_id'], unique=False)
    op.create_index(op.f('ix_law_changes_dept_name'), 'law_changes', ['dept_name'], unique=False)
    op.create_index(op.f('ix_law_changes_status'), 'law_changes', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_law_changes_status'), table_name='law_changes')
    op.drop_index(op.f('ix_law_changes_dept_name'), table_name='law_changes')
    op.drop_index(op.f('ix_law_changes_sync_batch_id'), table_name='law_changes')
    op.drop_index(op.f('ix_law_changes_sync_date'), table_name='law_changes')
    op.drop_index(op.f('ix_law_changes_law_id'), table_name='law_changes')
    op.drop_table('law_changes')

    # Enum 타입 삭제
    op.execute('DROP TYPE IF EXISTS apistatus')
    op.execute('DROP TYPE IF EXISTS changestatus')
