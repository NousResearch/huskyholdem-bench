"""tag_for_2025

Revision ID: 3f0dc6de8f99
Revises: 839be08c2b55
Create Date: 2025-07-25 06:27:40.403591

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3f0dc6de8f99'
down_revision: Union[str, None] = '839be08c2b55'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add the new column
    op.add_column('job', sa.Column('tournaments_2025_added', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    # Set all existing jobs to False (should be default, but explicit for clarity)
    op.execute('UPDATE job SET tournaments_2025_added = false')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('job', 'tournaments_2025_added')
