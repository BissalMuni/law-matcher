"""restructure parent_laws to laws and ordinance_law_mappings

기존 parent_laws 테이블을 다음 구조로 변경:
- laws: 상위법령 마스터 테이블 (API 응답 기반)
- ordinance_law_mappings: 조례-법령 연계 테이블

Revision ID: restructure_laws
Revises: update_parent_laws_dates
Create Date: 2025-12-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'restructure_laws'
down_revision: Union[str, None] = 'update_parent_laws_dates'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. laws 테이블 생성 (상위법령 마스터)
    op.create_table(
        'laws',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('law_serial_no', sa.BigInteger(), nullable=False),
        sa.Column('law_id', sa.BigInteger(), nullable=False),
        sa.Column('law_name', sa.String(500), nullable=False),
        sa.Column('law_abbr', sa.String(200), nullable=True),
        sa.Column('law_type', sa.String(50), nullable=False),
        sa.Column('proclaimed_date', sa.Date(), nullable=True),
        sa.Column('proclaimed_no', sa.Integer(), nullable=True),
        sa.Column('enforced_date', sa.Date(), nullable=True),
        sa.Column('revision_type', sa.String(50), nullable=True),
        sa.Column('history_code', sa.String(20), nullable=True),
        sa.Column('dept_name', sa.String(200), nullable=True),
        sa.Column('dept_code', sa.Integer(), nullable=True),
        sa.Column('joint_dept_info', sa.String(50), nullable=True),
        sa.Column('joint_proclaimed_no', sa.String(100), nullable=True),
        sa.Column('self_other_law', sa.String(20), nullable=True),
        sa.Column('detail_link', sa.String(500), nullable=True),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )

    # laws 테이블 인덱스 생성
    op.create_index('ix_laws_law_serial_no', 'laws', ['law_serial_no'], unique=True)
    op.create_index('ix_laws_law_id', 'laws', ['law_id'], unique=False)
    op.create_index('ix_laws_proclaimed_date', 'laws', ['proclaimed_date'], unique=False)

    # 2. ordinance_law_mappings 테이블 생성 (연계 테이블)
    op.create_table(
        'ordinance_law_mappings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ordinance_id', sa.Integer(), nullable=False),
        sa.Column('law_id', sa.Integer(), nullable=False),
        sa.Column('related_articles', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['ordinance_id'], ['ordinances.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['law_id'], ['laws.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ordinance_id', 'law_id', name='uq_ordinance_law')
    )

    # ordinance_law_mappings 인덱스 생성
    op.create_index('ix_ordinance_law_mappings_ordinance_id', 'ordinance_law_mappings', ['ordinance_id'])
    op.create_index('ix_ordinance_law_mappings_law_id', 'ordinance_law_mappings', ['law_id'])

    # 3. 기존 parent_laws 테이블 삭제 (데이터 마이그레이션은 별도 스크립트에서 처리)
    # 기존 데이터가 있다면 먼저 마이그레이션 후 삭제해야 함
    # 여기서는 새 테이블 구조만 생성하고, 데이터 마이그레이션은 서비스 로직에서 처리
    op.drop_table('parent_laws')

    # 4. law_amendments 테이블에 새 필드 추가
    op.add_column('law_amendments', sa.Column('ordinance_id', sa.Integer(), nullable=True))
    op.add_column('law_amendments', sa.Column('source_law_id', sa.Integer(), nullable=True))
    op.add_column('law_amendments', sa.Column('source_law_name', sa.String(500), nullable=True))
    op.add_column('law_amendments', sa.Column('source_proclaimed_date', sa.Date(), nullable=True))
    op.add_column('law_amendments', sa.Column('description', sa.String(1000), nullable=True))
    op.add_column('law_amendments', sa.Column('status', sa.String(20), server_default='PENDING'))

    op.create_foreign_key('fk_law_amendments_ordinance', 'law_amendments', 'ordinances', ['ordinance_id'], ['id'])
    op.create_foreign_key('fk_law_amendments_source_law', 'law_amendments', 'laws', ['source_law_id'], ['id'])


def downgrade() -> None:
    # 0. law_amendments 테이블 새 필드 제거
    op.drop_constraint('fk_law_amendments_source_law', 'law_amendments', type_='foreignkey')
    op.drop_constraint('fk_law_amendments_ordinance', 'law_amendments', type_='foreignkey')
    op.drop_column('law_amendments', 'status')
    op.drop_column('law_amendments', 'description')
    op.drop_column('law_amendments', 'source_proclaimed_date')
    op.drop_column('law_amendments', 'source_law_name')
    op.drop_column('law_amendments', 'source_law_id')
    op.drop_column('law_amendments', 'ordinance_id')

    # 1. parent_laws 테이블 재생성
    op.create_table(
        'parent_laws',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ordinance_id', sa.Integer(), nullable=False),
        sa.Column('law_id', sa.String(50), nullable=False),
        sa.Column('law_type', sa.String(20), nullable=False),
        sa.Column('law_name', sa.String(500), nullable=False),
        sa.Column('related_articles', sa.String(500), nullable=True),
        sa.Column('proclaimed_date', sa.Date(), nullable=True),
        sa.Column('enforced_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['ordinance_id'], ['ordinances.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. 새 테이블 삭제
    op.drop_index('ix_ordinance_law_mappings_law_id', 'ordinance_law_mappings')
    op.drop_index('ix_ordinance_law_mappings_ordinance_id', 'ordinance_law_mappings')
    op.drop_table('ordinance_law_mappings')

    op.drop_index('ix_laws_proclaimed_date', 'laws')
    op.drop_index('ix_laws_law_id', 'laws')
    op.drop_index('ix_laws_law_serial_no', 'laws')
    op.drop_table('laws')
