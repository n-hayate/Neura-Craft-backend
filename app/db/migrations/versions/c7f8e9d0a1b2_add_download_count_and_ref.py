"""add_download_count_and_ref

Revision ID: c7f8e9d0a1b2
Revises: 3a9d4d7e1b23
Create Date: 2025-11-21 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7f8e9d0a1b2'
down_revision: Union[str, None] = '3a9d4d7e1b23'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add download_count to files
    op.add_column('files', sa.Column('download_count', sa.Integer(), server_default='0', nullable=False))

    # Create file_references table
    op.create_table('file_references',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('file_id', sa.String(length=36), nullable=False),
        sa.Column('trial_id', sa.String(length=50), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['file_id'], ['files.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('file_id', 'user_id', 'trial_id', name='uix_file_user_trial')
    )
    op.create_index(op.f('ix_file_references_trial_id'), 'file_references', ['trial_id'], unique=False)

    # Expand trial_id in files to 50 characters
    # Check dialect to be safe, although sqlite usually ignores length
    bind = op.get_bind()
    if bind.dialect.name == 'mssql':
         op.alter_column('files', 'trial_id',
                   existing_type=sa.String(length=20),
                   type_=sa.String(length=50),
                   existing_nullable=False)
    else:
         # For other DBs (sqlite, postgres), just alter
         op.alter_column('files', 'trial_id',
                   existing_type=sa.String(length=20),
                   type_=sa.String(length=50),
                   existing_nullable=False)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == 'mssql':
         op.alter_column('files', 'trial_id',
                   existing_type=sa.String(length=50),
                   type_=sa.String(length=20),
                   existing_nullable=False)
    else:
         op.alter_column('files', 'trial_id',
                   existing_type=sa.String(length=50),
                   type_=sa.String(length=20),
                   existing_nullable=False)

    op.drop_index(op.f('ix_file_references_trial_id'), table_name='file_references')
    op.drop_table('file_references')
    op.drop_column('files', 'download_count')

