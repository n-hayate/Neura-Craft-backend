"""add file_extractions table

Revision ID: add_file_extractions_001
Revises: create_dl_table_001
Create Date: 2025-12-16 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "add_file_extractions_001"
down_revision: Union[str, None] = "create_dl_table_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "file_extractions",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("file_id", sa.String(length=36), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
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
        sa.ForeignKeyConstraint(["file_id"], ["files.id"]),
        sa.UniqueConstraint("file_id", name="uq_file_extractions_file_id"),
    )
    op.create_index(op.f("ix_file_extractions_file_id"), "file_extractions", ["file_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_file_extractions_file_id"), table_name="file_extractions")
    op.drop_table("file_extractions")



