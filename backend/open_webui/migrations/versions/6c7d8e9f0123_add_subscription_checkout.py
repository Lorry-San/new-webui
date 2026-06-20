"""add subscription checkout table

Revision ID: 6c7d8e9f0123
Revises: 5b6c7d8e9f01
Create Date: 2026-06-21
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = '6c7d8e9f0123'
down_revision: Union[str, None] = '5b6c7d8e9f01'
branch_labels = None
depends_on = None


def _index_exists(inspector, index_name, table_name):
    indexes = inspector.get_indexes(table_name)
    return any(idx['name'] == index_name for idx in indexes)


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'subscription_checkout' not in tables:
        op.create_table(
            'subscription_checkout',
            sa.Column('id', sa.Text(), primary_key=True),
            sa.Column('user_id', sa.Text(), nullable=False),
            sa.Column('plan_id', sa.Text(), nullable=False),
            sa.Column('status', sa.Text(), nullable=False, default='pending'),
            sa.Column('amount', sa.Float(), nullable=False, default=0),
            sa.Column('currency', sa.Text(), nullable=False, default='USD'),
            sa.Column('interval', sa.Text(), nullable=False, default='month'),
            sa.Column('checkout_url', sa.Text(), nullable=True),
            sa.Column('metadata', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
            sa.Column('updated_at', sa.BigInteger(), nullable=False),
            sa.Column('completed_at', sa.BigInteger(), nullable=True),
        )

    inspector.clear_cache()
    if 'subscription_checkout' in inspector.get_table_names():
        for index_name, columns in {
            'ix_subscription_checkout_user_id': ['user_id'],
            'ix_subscription_checkout_plan_id': ['plan_id'],
            'ix_subscription_checkout_status': ['status'],
            'ix_subscription_checkout_created_at': ['created_at'],
        }.items():
            if not _index_exists(inspector, index_name, 'subscription_checkout'):
                op.create_index(index_name, 'subscription_checkout', columns)


def downgrade():
    inspector = sa.inspect(op.get_bind())
    if 'subscription_checkout' not in inspector.get_table_names():
        return
    for index_name in [
        'ix_subscription_checkout_created_at',
        'ix_subscription_checkout_status',
        'ix_subscription_checkout_plan_id',
        'ix_subscription_checkout_user_id',
    ]:
        if _index_exists(inspector, index_name, 'subscription_checkout'):
            op.drop_index(index_name, table_name='subscription_checkout')
    op.drop_table('subscription_checkout')
