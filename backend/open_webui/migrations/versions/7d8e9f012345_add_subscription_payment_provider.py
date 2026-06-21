"""add subscription payment provider table

Revision ID: 7d8e9f012345
Revises: 6c7d8e9f0123
Create Date: 2026-06-21
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = '7d8e9f012345'
down_revision: Union[str, None] = '6c7d8e9f0123'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'subscription_payment_provider' not in inspector.get_table_names():
        op.create_table(
            'subscription_payment_provider',
            sa.Column('id', sa.Text(), primary_key=True),
            sa.Column('name', sa.Text(), nullable=False),
            sa.Column('provider_type', sa.Text(), nullable=False, default='manual'),
            sa.Column('config', sa.JSON(), nullable=False, default={}),
            sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
            sa.Column('sort_order', sa.BigInteger(), nullable=False, default=0),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
            sa.Column('updated_at', sa.BigInteger(), nullable=False),
        )


def downgrade():
    inspector = sa.inspect(op.get_bind())
    if 'subscription_payment_provider' in inspector.get_table_names():
        op.drop_table('subscription_payment_provider')
