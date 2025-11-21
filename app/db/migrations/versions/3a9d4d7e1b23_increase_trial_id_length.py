"""Increase trial_id length to 20 characters

Revision ID: 3a9d4d7e1b23
Revises: 2f0a3eb36a24
Create Date: 2025-11-21 01:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3a9d4d7e1b23"
down_revision: Union[str, None] = "2f0a3eb36a24"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Azure SQL (MSSQL) 上の files.trial_id の長さを 4 -> 20 に拡張."""
    bind = op.get_bind()
    if bind.dialect.name != "mssql":
        # SQLite 等では長さ制約が実質効いておらず、変更不要
        return

    op.alter_column(
        "files",
        "trial_id",
        existing_type=sa.String(4),
        type_=sa.String(20),
        existing_nullable=False,
    )


def downgrade() -> None:
    """MSSQL 上の files.trial_id を 20 -> 4 に戻す."""
    bind = op.get_bind()
    if bind.dialect.name != "mssql":
        return

    op.alter_column(
        "files",
        "trial_id",
        existing_type=sa.String(20),
        type_=sa.String(4),
        existing_nullable=False,
    )



