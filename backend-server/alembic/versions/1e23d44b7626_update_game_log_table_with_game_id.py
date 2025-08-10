"""update game log table with game id

Revision ID: 1e23d44b7626
Revises: 878593718358
Create Date: 2025-07-17 07:26:11.944803

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '1e23d44b7626'
down_revision: Union[str, None] = '878593718358'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop unique index on game_uuid and make column nullable
    op.drop_index(op.f('ix_game_logs_game_uuid'), table_name='game_logs')
    op.alter_column('game_logs', 'game_uuid',
               existing_type=sa.VARCHAR(),
               nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    # Restore game_uuid as not nullable and add unique index back
    op.alter_column('game_logs', 'game_uuid',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.create_index(op.f('ix_game_logs_game_uuid'), 'game_logs', ['game_uuid'], unique=True)
