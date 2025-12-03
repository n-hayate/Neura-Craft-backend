"""create file downloads table

Revision ID: create_dl_table_001
Revises: fix_blob_name_001
Create Date: 2025-12-02 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'create_dl_table_001'
down_revision = '6c359e2e8af1'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'file_downloads',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('file_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('downloaded_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['file_id'], ['files.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_file_downloads_file_id'), 'file_downloads', ['file_id'], unique=False)
    op.create_index(op.f('ix_file_downloads_user_id'), 'file_downloads', ['user_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_file_downloads_user_id'), table_name='file_downloads')
    op.drop_index(op.f('ix_file_downloads_file_id'), table_name='file_downloads')
    op.drop_table('file_downloads')

