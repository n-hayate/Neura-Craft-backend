"""fix_blob_name_nvarchar

Revision ID: fix_blob_name_001
Revises: force_nvarchar_001
Create Date: 2025-11-23 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'fix_blob_name_001'
down_revision: Union[str, None] = 'force_nvarchar_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != 'mssql':
        return

    # 強力な制約削除スクリプト
    # blob_name カラムに関連する UNIQUE制約、DEFAULT制約、インデックスを全て削除する
    op.execute("""
        DECLARE @TableName NVARCHAR(256) = 'files'
        DECLARE @ColumnName NVARCHAR(256) = 'blob_name'
        DECLARE @ConstraintName NVARCHAR(256)
        DECLARE @Sql NVARCHAR(MAX)

        -- 1. UNIQUE制約 / CHECK制約 / DEFAULT制約 の削除
        DECLARE cur CURSOR FOR
            SELECT kc.name
            FROM sys.key_constraints kc
            JOIN sys.index_columns ic ON kc.parent_object_id = ic.object_id AND kc.unique_index_id = ic.index_id
            JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
            WHERE kc.parent_object_id = OBJECT_ID(@TableName)
            AND c.name = @ColumnName
        
        OPEN cur
        FETCH NEXT FROM cur INTO @ConstraintName
        WHILE @@FETCH_STATUS = 0
        BEGIN
            SET @Sql = 'ALTER TABLE ' + @TableName + ' DROP CONSTRAINT ' + @ConstraintName
            EXEC sp_executesql @Sql
            FETCH NEXT FROM cur INTO @ConstraintName
        END
        CLOSE cur
        DEALLOCATE cur

        -- 2. 純粋なインデックスの削除
        DECLARE cur_idx CURSOR FOR
            SELECT i.name
            FROM sys.indexes i
            JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
            JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
            WHERE i.object_id = OBJECT_ID(@TableName)
            AND c.name = @ColumnName
            AND i.is_primary_key = 0 -- PKは消さない
            AND i.is_unique_constraint = 0 -- 制約付きインデックスは上で消えているはずだが念のため
        
        OPEN cur_idx
        FETCH NEXT FROM cur_idx INTO @ConstraintName
        WHILE @@FETCH_STATUS = 0
        BEGIN
            SET @Sql = 'DROP INDEX ' + @ConstraintName + ' ON ' + @TableName
            EXEC sp_executesql @Sql
            FETCH NEXT FROM cur_idx INTO @ConstraintName
        END
        CLOSE cur_idx
        DEALLOCATE cur_idx
    """)

    # Alter column to NVARCHAR
    op.alter_column('files', 'blob_name',
               existing_type=sa.VARCHAR(length=512),
               type_=sa.NVARCHAR(length=512),
               existing_nullable=False)

    # Recreate Unique Constraint
    op.create_unique_constraint('uq_files_blob_name', 'files', ['blob_name'])


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != 'mssql':
        return

    op.drop_constraint('uq_files_blob_name', 'files', type_='unique')

    op.alter_column('files', 'blob_name',
               existing_type=sa.NVARCHAR(length=512),
               type_=sa.VARCHAR(length=512),
               existing_nullable=False)
               
    # 元の名前がわからないので、ここでも新規作成
    # op.create_unique_constraint('uq_files_blob_name', 'files', ['blob_name'])
