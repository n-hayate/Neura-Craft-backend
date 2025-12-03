"""merge heads for files v2

Revision ID: f743894ea518
Revises: bf9d9f4ffc23, ff59e5879b0b
Create Date: 2025-12-02 19:21:38.941780

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f743894ea518'
down_revision: Union[str, None] = ('bf9d9f4ffc23', 'ff59e5879b0b')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass


