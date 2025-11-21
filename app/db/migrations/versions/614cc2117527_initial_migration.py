"""Initial migration

Revision ID: 614cc2117527
Revises:
Create Date: 2025-11-19 14:20:02.535076

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "614cc2117527"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """ユーザーおよびファイルテーブルの初期作成."""
    # users テーブル
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("1")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # files テーブル
    op.create_table(
        "files",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("blob_name", sa.String(512), nullable=False, unique=True),
        sa.Column("content_type", sa.String(128), nullable=True),
        sa.Column("file_size", sa.Integer, nullable=True),
        sa.Column("azure_blob_url", sa.String(1024), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        # メタデータフィールド（現行モデル準拠）
        sa.Column("final_product", sa.String(255), nullable=False),
        sa.Column("issue", sa.String(255), nullable=False),
        sa.Column("ingredient", sa.String(255), nullable=False),
        sa.Column("customer", sa.String(255), nullable=False),
        sa.Column("trial_id", sa.String(20), nullable=False),
        sa.Column("author", sa.String(255), nullable=True),
        sa.Column("file_extension", sa.String(10), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default="active",
        ),
    )
    op.create_index("ix_files_owner_id", "files", ["owner_id"])
    op.create_index("ix_files_final_product", "files", ["final_product"])
    op.create_index("ix_files_issue", "files", ["issue"])
    op.create_index("ix_files_ingredient", "files", ["ingredient"])
    op.create_index("ix_files_customer", "files", ["customer"])
    op.create_index("ix_files_trial_id", "files", ["trial_id"])
    op.create_index("ix_files_author", "files", ["author"])
    op.create_index("ix_files_updated_at", "files", ["updated_at"])


def downgrade() -> None:
    """テーブルとインデックスの削除."""
    # files から先に削除（FK制約のため）
    op.drop_index("ix_files_updated_at", table_name="files")
    op.drop_index("ix_files_author", table_name="files")
    op.drop_index("ix_files_trial_id", table_name="files")
    op.drop_index("ix_files_customer", table_name="files")
    op.drop_index("ix_files_ingredient", table_name="files")
    op.drop_index("ix_files_issue", table_name="files")
    op.drop_index("ix_files_final_product", table_name="files")
    op.drop_index("ix_files_owner_id", table_name="files")
    op.drop_table("files")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

