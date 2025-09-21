"""add s3_url and scan fields to files

Revision ID: files_add_s3_and_scan_20250920
Revises: add_users_table_20250920
Create Date: 2025-09-20 01:00:01
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'files_add_s3_and_scan_20250920'
down_revision = 'add_users_table_20250920'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('files', sa.Column('s3_url', sa.String(length=1000), nullable=True))
    op.add_column('files', sa.Column('scan_status', sa.String(length=50), nullable=True, server_default='pending'))
    op.add_column('files', sa.Column('scan_result', sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column('files', 'scan_result')
    op.drop_column('files', 'scan_status')
    op.drop_column('files', 's3_url')

