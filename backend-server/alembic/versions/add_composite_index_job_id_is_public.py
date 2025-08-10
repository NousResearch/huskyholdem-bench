"""Add composite index on job_id and is_public for game_logs

Revision ID: comp_idx_job_public
Revises: 3f0dc6de8f99
Create Date: 2025-01-27 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'comp_idx_job_public'
down_revision: Union[str, None] = '3f0dc6de8f99'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create composite index on job_id and is_public for better query performance
    op.create_index(
        'ix_game_logs_job_id_is_public',
        'game_logs',
        ['job_id', 'is_public'],
        unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop the composite index
    op.drop_index('ix_game_logs_job_id_is_public', table_name='game_logs') 