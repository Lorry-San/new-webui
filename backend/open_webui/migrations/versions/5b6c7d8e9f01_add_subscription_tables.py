"""add subscription tables

Revision ID: 5b6c7d8e9f01
Revises: 461111b60977
Create Date: 2026-06-20
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = '5b6c7d8e9f01'
down_revision: Union[str, None] = '461111b60977'
branch_labels = None
depends_on = None


def _index_exists(inspector, index_name, table_name):
    indexes = inspector.get_indexes(table_name)
    return any(idx['name'] == index_name for idx in indexes)


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'subscription_plan' not in tables:
        op.create_table(
            'subscription_plan',
            sa.Column('id', sa.Text(), primary_key=True),
            sa.Column('name', sa.Text(), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('price', sa.Float(), nullable=False, default=0),
            sa.Column('currency', sa.Text(), nullable=False, default='USD'),
            sa.Column('interval', sa.Text(), nullable=False, default='month'),
            sa.Column('features', sa.JSON(), nullable=True),
            sa.Column('rules', sa.JSON(), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
            sa.Column('sort_order', sa.BigInteger(), nullable=False, default=0),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
            sa.Column('updated_at', sa.BigInteger(), nullable=False),
        )

    if 'user_subscription' not in tables:
        op.create_table(
            'user_subscription',
            sa.Column('id', sa.Text(), primary_key=True),
            sa.Column('user_id', sa.Text(), nullable=False),
            sa.Column('plan_id', sa.Text(), nullable=False),
            sa.Column('status', sa.Text(), nullable=False, default='active'),
            sa.Column('current_period_start', sa.BigInteger(), nullable=True),
            sa.Column('current_period_end', sa.BigInteger(), nullable=True),
            sa.Column('metadata', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
            sa.Column('updated_at', sa.BigInteger(), nullable=False),
        )

    if 'subscription_usage_event' not in tables:
        op.create_table(
            'subscription_usage_event',
            sa.Column('id', sa.Text(), primary_key=True),
            sa.Column('user_id', sa.Text(), nullable=False),
            sa.Column('plan_id', sa.Text(), nullable=False),
            sa.Column('model_id', sa.Text(), nullable=True),
            sa.Column('chat_id', sa.Text(), nullable=True),
            sa.Column('message_id', sa.Text(), nullable=True),
            sa.Column('input_tokens', sa.BigInteger(), nullable=False, default=0),
            sa.Column('output_tokens', sa.BigInteger(), nullable=False, default=0),
            sa.Column('total_tokens', sa.BigInteger(), nullable=False, default=0),
            sa.Column('amount', sa.Float(), nullable=False, default=0),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
        )

    inspector.clear_cache()
    if 'user_subscription' in inspector.get_table_names():
        if not _index_exists(inspector, 'ix_user_subscription_user_id', 'user_subscription'):
            op.create_index('ix_user_subscription_user_id', 'user_subscription', ['user_id'])
        if not _index_exists(inspector, 'ix_user_subscription_plan_id', 'user_subscription'):
            op.create_index('ix_user_subscription_plan_id', 'user_subscription', ['plan_id'])
        if not _index_exists(inspector, 'ix_user_subscription_user_status', 'user_subscription'):
            op.create_index('ix_user_subscription_user_status', 'user_subscription', ['user_id', 'status'])

    if 'subscription_usage_event' in inspector.get_table_names():
        for index_name, columns in {
            'ix_subscription_usage_event_user_id': ['user_id'],
            'ix_subscription_usage_event_plan_id': ['plan_id'],
            'ix_subscription_usage_event_model_id': ['model_id'],
            'ix_subscription_usage_event_created_at': ['created_at'],
        }.items():
            if not _index_exists(inspector, index_name, 'subscription_usage_event'):
                op.create_index(index_name, 'subscription_usage_event', columns)


def downgrade():
    op.drop_table('subscription_usage_event')
    op.drop_table('user_subscription')
    op.drop_table('subscription_plan')
