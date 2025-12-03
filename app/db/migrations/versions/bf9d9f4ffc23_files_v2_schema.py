"""files v2 schema

Revision ID: bf9d9f4ffc23
Revises: force_nvarchar_001
Create Date: 2025-12-02 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "bf9d9f4ffc23"
down_revision: Union[str, None] = "force_nvarchar_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ローカル反映:
    # alembic upgrade head

    # 既存の参照テーブルを先に削除（外部キー制約のため）
    op.drop_table("file_references")
    op.drop_table("files")

    op.create_table(
        "files",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("blob_path", sa.String(length=512), nullable=False, unique=True),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("application", sa.String(length=255), nullable=True),
        sa.Column("issue", sa.String(length=255), nullable=True),
        sa.Column("ingredient", sa.String(length=255), nullable=True),
        sa.Column("customer", sa.String(length=255), nullable=True),
        sa.Column("trial_id", sa.String(length=255), nullable=True),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column(
            "owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "file_references",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("file_id", sa.String(length=36), sa.ForeignKey("files.id"), nullable=False),
        sa.Column("trial_id", sa.String(length=50), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("file_id", "user_id", "trial_id", name="uix_file_user_trial"),
    )

    op.create_index("ix_files_owner_id", "files", ["owner_id"])
    op.create_index("ix_file_references_trial_id", "file_references", ["trial_id"])


def downgrade() -> None:
    op.drop_table("file_references")
    op.drop_table("files")

    # 旧構成を再作成（DDLは force_nvarchar_001 相当）
    op.create_table(
        "files",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("original_filename", sa.Unicode(length=255), nullable=False),
        sa.Column("blob_name", sa.Unicode(length=512), nullable=False, unique=True),
        sa.Column("content_type", sa.String(length=128), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("azure_blob_url", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("final_product", sa.Unicode(length=255), nullable=False),
        sa.Column("issue", sa.Unicode(length=255), nullable=False),
        sa.Column("ingredient", sa.Unicode(length=255), nullable=False),
        sa.Column("customer", sa.Unicode(length=255), nullable=False),
        sa.Column("trial_id", sa.Unicode(length=50), nullable=False),
        sa.Column("author", sa.Unicode(length=255), nullable=True),
        sa.Column("file_extension", sa.String(length=10), nullable=False),
        sa.Column("download_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("is_preview_hidden", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_index("ix_files_owner_id", "files", ["owner_id"])

    op.create_table(
        "file_references",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("file_id", sa.String(length=36), sa.ForeignKey("files.id"), nullable=False),
        sa.Column("trial_id", sa.Unicode(length=50), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("file_id", "user_id", "trial_id", name="uix_file_user_trial"),
    )

    op.create_index("ix_file_references_trial_id", "file_references", ["trial_id"])

