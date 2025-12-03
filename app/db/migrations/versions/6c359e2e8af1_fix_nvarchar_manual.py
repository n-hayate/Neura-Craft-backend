"""fix_nvarchar_manual

Revision ID: 6c359e2e8af1
Revises: f743894ea518
Create Date: 2025-12-03 06:01:54.933694

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6c359e2e8af1'
down_revision: Union[str, None] = 'f743894ea518'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('files', 'original_name', type_=sa.Unicode(255), existing_type=sa.String(255), nullable=False)
    op.alter_column('files', 'application', type_=sa.Unicode(255), existing_type=sa.String(255), nullable=True)
    op.alter_column('files', 'issue', type_=sa.Unicode(255), existing_type=sa.String(255), nullable=True)
    op.alter_column('files', 'ingredient', type_=sa.Unicode(255), existing_type=sa.String(255), nullable=True)
    op.alter_column('files', 'customer', type_=sa.Unicode(255), existing_type=sa.String(255), nullable=True)
    op.alter_column('files', 'trial_id', type_=sa.Unicode(255), existing_type=sa.String(255), nullable=True)
    op.alter_column('files', 'author', type_=sa.Unicode(255), existing_type=sa.String(255), nullable=True)


def downgrade() -> None:
    op.alter_column('files', 'original_name', type_=sa.String(255), existing_type=sa.Unicode(255), nullable=False)
    op.alter_column('files', 'application', type_=sa.String(255), existing_type=sa.Unicode(255), nullable=True)
    op.alter_column('files', 'issue', type_=sa.String(255), existing_type=sa.Unicode(255), nullable=True)
    op.alter_column('files', 'ingredient', type_=sa.String(255), existing_type=sa.Unicode(255), nullable=True)
    op.alter_column('files', 'customer', type_=sa.String(255), existing_type=sa.Unicode(255), nullable=True)
    op.alter_column('files', 'trial_id', type_=sa.String(255), existing_type=sa.Unicode(255), nullable=True)
    op.alter_column('files', 'author', type_=sa.String(255), existing_type=sa.Unicode(255), nullable=True)


