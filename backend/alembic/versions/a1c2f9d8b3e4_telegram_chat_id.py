"""telegram chat id

Revision ID: a1c2f9d8b3e4
Revises: 39d41d1deb68
Create Date: 2026-09-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1c2f9d8b3e4'
down_revision: Union[str, None] = '39d41d1deb68'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("telegram_chat_id", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "telegram_chat_id")
