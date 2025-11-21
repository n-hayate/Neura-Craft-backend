"""add_file_metadata_columns

Revision ID: add_file_metadata_001
Revises: 614cc2117527
Create Date: 2025-01-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import NoSuchTableError


# revision identifiers, used by Alembic.
revision: str = '2f0a3eb36a24'
down_revision: Union[str, None] = '614cc2117527'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Azure SQL（MSSQL）の新規DBでは、初期マイグレーションで既に
    # 最終的なスキーマ（メタデータカラム・インデックス含む）が作成される想定のため、
    # このマイグレーションは実質的に何もしないようにする。
    if conn.dialect.name == "mssql":
        return

    inspector = sa.inspect(conn)
    try:
        # メタデータカラムを追加（既に存在する場合はスキップ）
        existing_columns = [col["name"] for col in inspector.get_columns("files")]
    except NoSuchTableError:
        # 新規DBで、まだ files テーブルが存在しない場合は何もしない
        # （初期マイグレーション側で最新スキーマのテーブルを作成する想定）
        return
    
    columns_to_add = {
        'final_product': sa.Column('final_product', sa.String(255), nullable=True),
        'issue': sa.Column('issue', sa.String(255), nullable=True),
        'ingredient': sa.Column('ingredient', sa.String(255), nullable=True),
        'customer': sa.Column('customer', sa.String(255), nullable=True),
        'trial_id': sa.Column('trial_id', sa.String(4), nullable=True),
        'author': sa.Column('author', sa.String(255), nullable=True),
        'file_extension': sa.Column('file_extension', sa.String(10), nullable=True),
        'updated_at': sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        'status': sa.Column('status', sa.String(50), nullable=True),
    }
    
    for col_name, col_def in columns_to_add.items():
        if col_name not in existing_columns:
            op.add_column('files', col_def)
    
    # 再度カラムリストを取得（追加後）
    inspector = sa.inspect(conn)
    existing_columns_after = [col['name'] for col in inspector.get_columns('files')]
    
    # 既存データにデフォルト値を設定
    if 'final_product' in existing_columns_after:
        op.execute("UPDATE files SET final_product = '未設定' WHERE final_product IS NULL")
    if 'issue' in existing_columns_after:
        op.execute("UPDATE files SET issue = '未設定' WHERE issue IS NULL")
    if 'ingredient' in existing_columns_after:
        op.execute("UPDATE files SET ingredient = '未設定' WHERE ingredient IS NULL")
    if 'customer' in existing_columns_after:
        op.execute("UPDATE files SET customer = '未設定' WHERE customer IS NULL")
    if 'trial_id' in existing_columns_after:
        op.execute("UPDATE files SET trial_id = '0000' WHERE trial_id IS NULL")
    if 'file_extension' in existing_columns_after:
        op.execute("UPDATE files SET file_extension = 'unknown' WHERE file_extension IS NULL")
    if 'updated_at' in existing_columns_after:
        op.execute("UPDATE files SET updated_at = created_at WHERE updated_at IS NULL")
    if 'status' in existing_columns_after:
        op.execute("UPDATE files SET status = 'active' WHERE status IS NULL")
    
    # NOT NULL制約を追加（SQLiteでは既存のNULL値がないことを確認してから実行）
    if 'final_product' in existing_columns_after:
        op.alter_column('files', 'final_product', nullable=False)
    if 'issue' in existing_columns_after:
        op.alter_column('files', 'issue', nullable=False)
    if 'ingredient' in existing_columns_after:
        op.alter_column('files', 'ingredient', nullable=False)
    if 'customer' in existing_columns_after:
        op.alter_column('files', 'customer', nullable=False)
    if 'trial_id' in existing_columns_after:
        op.alter_column('files', 'trial_id', nullable=False)
    if 'file_extension' in existing_columns_after:
        op.alter_column('files', 'file_extension', nullable=False)
    if 'updated_at' in existing_columns_after:
        op.alter_column('files', 'updated_at', nullable=False)
    if 'status' in existing_columns_after:
        op.alter_column('files', 'status', nullable=False)
    
    # インデックスを追加（既に存在する場合はスキップ）
    existing_indexes = [idx['name'] for idx in inspector.get_indexes('files')]
    
    if 'ix_files_final_product' not in existing_indexes and 'final_product' in existing_columns_after:
        op.create_index(op.f('ix_files_final_product'), 'files', ['final_product'], unique=False)
    if 'ix_files_issue' not in existing_indexes and 'issue' in existing_columns_after:
        op.create_index(op.f('ix_files_issue'), 'files', ['issue'], unique=False)
    if 'ix_files_ingredient' not in existing_indexes and 'ingredient' in existing_columns_after:
        op.create_index(op.f('ix_files_ingredient'), 'files', ['ingredient'], unique=False)
    if 'ix_files_customer' not in existing_indexes and 'customer' in existing_columns_after:
        op.create_index(op.f('ix_files_customer'), 'files', ['customer'], unique=False)
    if 'ix_files_trial_id' not in existing_indexes and 'trial_id' in existing_columns_after:
        op.create_index(op.f('ix_files_trial_id'), 'files', ['trial_id'], unique=False)
    if 'ix_files_author' not in existing_indexes and 'author' in existing_columns_after:
        op.create_index(op.f('ix_files_author'), 'files', ['author'], unique=False)
    if 'ix_files_updated_at' not in existing_indexes and 'updated_at' in existing_columns_after:
        op.create_index(op.f('ix_files_updated_at'), 'files', ['updated_at'], unique=False)


def downgrade() -> None:
    # インデックスを削除
    op.drop_index(op.f('ix_files_updated_at'), table_name='files')
    op.drop_index(op.f('ix_files_author'), table_name='files')
    op.drop_index(op.f('ix_files_trial_id'), table_name='files')
    op.drop_index(op.f('ix_files_customer'), table_name='files')
    op.drop_index(op.f('ix_files_ingredient'), table_name='files')
    op.drop_index(op.f('ix_files_issue'), table_name='files')
    op.drop_index(op.f('ix_files_final_product'), table_name='files')
    
    # カラムを削除
    op.drop_column('files', 'status')
    op.drop_column('files', 'updated_at')
    op.drop_column('files', 'file_extension')
    op.drop_column('files', 'author')
    op.drop_column('files', 'trial_id')
    op.drop_column('files', 'customer')
    op.drop_column('files', 'ingredient')
    op.drop_column('files', 'issue')
    op.drop_column('files', 'final_product')

