"""add users table

Revision ID: add_users_table_20250920
Revises: 
Create Date: 2025-09-20 00:00:01
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_users_table_20250920'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('username', sa.String(length=100), nullable=False, unique=True, index=True),
        sa.Column('email', sa.String(length=200), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(length=200), nullable=False),
        sa.Column('roles', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('users')

