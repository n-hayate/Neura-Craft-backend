"""fix_varchar_to_nvarchar_manual

Revision ID: force_nvarchar_001
Revises: c7f8e9d0a1b2
Create Date: 2025-11-23 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'force_nvarchar_001'
down_revision: Union[str, None] = 'c7f8e9d0a1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if we are running on MSSQL
    bind = op.get_bind()
    if bind.dialect.name != 'mssql':
        return

    # Drop indexes first
    op.drop_index('ix_files_final_product', table_name='files')
    op.drop_index('ix_files_issue', table_name='files')
    op.drop_index('ix_files_ingredient', table_name='files')
    op.drop_index('ix_files_customer', table_name='files')
    op.drop_index('ix_files_trial_id', table_name='files')
    op.drop_index('ix_files_author', table_name='files')
    # We also need to drop the unique constraint on file_references that depends on trial_id
    # But trial_id in file_references is new, so maybe it's fine?
    # Wait, trial_id in file_references is also String. We should change it too.
    
    # Also file_references.trial_id has an index
    op.drop_index('ix_file_references_trial_id', table_name='file_references')
    # And the unique constraint... 
    # Unique constraint 'uix_file_user_trial' depends on trial_id
    op.drop_constraint('uix_file_user_trial', 'file_references', type_='unique')


    # Force alter columns to NVARCHAR
    # files table
    op.alter_column('files', 'original_filename',
               existing_type=sa.VARCHAR(length=255),
               type_=sa.NVARCHAR(length=255),
               existing_nullable=False)
               
    op.alter_column('files', 'final_product',
               existing_type=sa.VARCHAR(length=255),
               type_=sa.NVARCHAR(length=255),
               existing_nullable=False)

    op.alter_column('files', 'issue',
               existing_type=sa.VARCHAR(length=255),
               type_=sa.NVARCHAR(length=255),
               existing_nullable=False)

    op.alter_column('files', 'ingredient',
               existing_type=sa.VARCHAR(length=255),
               type_=sa.NVARCHAR(length=255),
               existing_nullable=False)

    op.alter_column('files', 'customer',
               existing_type=sa.VARCHAR(length=255),
               type_=sa.NVARCHAR(length=255),
               existing_nullable=False)
               
    op.alter_column('files', 'trial_id',
               existing_type=sa.VARCHAR(length=50),
               type_=sa.NVARCHAR(length=50),
               existing_nullable=False)

    op.alter_column('files', 'author',
               existing_type=sa.VARCHAR(length=255),
               type_=sa.NVARCHAR(length=255),
               existing_nullable=True)

    # users table
    op.alter_column('users', 'full_name',
               existing_type=sa.VARCHAR(length=255),
               type_=sa.NVARCHAR(length=255),
               existing_nullable=True)

    # file_references table
    op.alter_column('file_references', 'trial_id',
               existing_type=sa.VARCHAR(length=50),
               type_=sa.NVARCHAR(length=50),
               existing_nullable=False)


    # Recreate indexes
    op.create_index('ix_files_final_product', 'files', ['final_product'])
    op.create_index('ix_files_issue', 'files', ['issue'])
    op.create_index('ix_files_ingredient', 'files', ['ingredient'])
    op.create_index('ix_files_customer', 'files', ['customer'])
    op.create_index('ix_files_trial_id', 'files', ['trial_id'])
    op.create_index('ix_files_author', 'files', ['author'])
    
    op.create_index('ix_file_references_trial_id', 'file_references', ['trial_id'])
    
    # Recreate unique constraint
    op.create_unique_constraint('uix_file_user_trial', 'file_references', ['file_id', 'user_id', 'trial_id'])


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != 'mssql':
        return

    # Drop indexes first
    op.drop_index('ix_files_final_product', table_name='files')
    op.drop_index('ix_files_issue', table_name='files')
    op.drop_index('ix_files_ingredient', table_name='files')
    op.drop_index('ix_files_customer', table_name='files')
    op.drop_index('ix_files_trial_id', table_name='files')
    op.drop_index('ix_files_author', table_name='files')
    op.drop_index('ix_file_references_trial_id', table_name='file_references')
    op.drop_constraint('uix_file_user_trial', 'file_references', type_='unique')

    # Revert to VARCHAR
    op.alter_column('file_references', 'trial_id',
               existing_type=sa.NVARCHAR(length=50),
               type_=sa.VARCHAR(length=50),
               existing_nullable=False)

    op.alter_column('users', 'full_name',
               existing_type=sa.NVARCHAR(length=255),
               type_=sa.VARCHAR(length=255),
               existing_nullable=True)

    op.alter_column('files', 'author',
               existing_type=sa.NVARCHAR(length=255),
               type_=sa.VARCHAR(length=255),
               existing_nullable=True)

    op.alter_column('files', 'trial_id',
               existing_type=sa.NVARCHAR(length=50),
               type_=sa.VARCHAR(length=50),
               existing_nullable=False)

    op.alter_column('files', 'customer',
               existing_type=sa.NVARCHAR(length=255),
               type_=sa.VARCHAR(length=255),
               existing_nullable=False)

    op.alter_column('files', 'ingredient',
               existing_type=sa.NVARCHAR(length=255),
               type_=sa.VARCHAR(length=255),
               existing_nullable=False)

    op.alter_column('files', 'issue',
               existing_type=sa.NVARCHAR(length=255),
               type_=sa.VARCHAR(length=255),
               existing_nullable=False)

    op.alter_column('files', 'final_product',
               existing_type=sa.NVARCHAR(length=255),
               type_=sa.VARCHAR(length=255),
               existing_nullable=False)

    op.alter_column('files', 'original_filename',
               existing_type=sa.NVARCHAR(length=255),
               type_=sa.VARCHAR(length=255),
               existing_nullable=False)

    # Recreate indexes
    op.create_index('ix_files_final_product', 'files', ['final_product'])
    op.create_index('ix_files_issue', 'files', ['issue'])
    op.create_index('ix_files_ingredient', 'files', ['ingredient'])
    op.create_index('ix_files_customer', 'files', ['customer'])
    op.create_index('ix_files_trial_id', 'files', ['trial_id'])
    op.create_index('ix_files_author', 'files', ['author'])
    op.create_index('ix_file_references_trial_id', 'file_references', ['trial_id'])
    op.create_unique_constraint('uix_file_user_trial', 'file_references', ['file_id', 'user_id', 'trial_id'])
