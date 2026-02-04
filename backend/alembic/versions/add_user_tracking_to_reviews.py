"""add user tracking to ordinance_reviews

Revision ID: add_user_tracking_to_reviews
Revises: add_users_table
Create Date: 2024-02-04 00:00:01.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_user_tracking_to_reviews'
down_revision = 'add_users_table'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add created_by_id and updated_by_id columns to ordinance_reviews
    op.add_column('ordinance_reviews', sa.Column('created_by_id', sa.Integer(), nullable=True))
    op.add_column('ordinance_reviews', sa.Column('updated_by_id', sa.Integer(), nullable=True))

    # Add foreign key constraints
    op.create_foreign_key(
        'fk_ordinance_reviews_created_by_id',
        'ordinance_reviews', 'users',
        ['created_by_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_ordinance_reviews_updated_by_id',
        'ordinance_reviews', 'users',
        ['updated_by_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    # Drop foreign key constraints
    op.drop_constraint('fk_ordinance_reviews_updated_by_id', 'ordinance_reviews', type_='foreignkey')
    op.drop_constraint('fk_ordinance_reviews_created_by_id', 'ordinance_reviews', type_='foreignkey')

    # Drop columns
    op.drop_column('ordinance_reviews', 'updated_by_id')
    op.drop_column('ordinance_reviews', 'created_by_id')
