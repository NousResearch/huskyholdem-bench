"""add_llm_batch_run_to_jobtype_enum

Revision ID: 4e01ebd44c42
Revises: f910fa98f728
Create Date: 2025-08-09 20:29:21.493261

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '4e01ebd44c42'
down_revision: Union[str, None] = 'f910fa98f728'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add LLM_BATCH_RUN to the existing jobtype enum
    op.execute("ALTER TYPE jobtype ADD VALUE 'LLM_BATCH_RUN'")


def downgrade() -> None:
    """Downgrade schema."""
    # PostgreSQL doesn't support DROP VALUE, so we need to recreate the enum
    
    # Step 1: Create a new enum without llm_batch_run
    op.execute("CREATE TYPE jobtype_new AS ENUM ('SIM_USER', 'SIM_ADMIN', 'SCALING')")
    
    # Step 2: Update the job table to use the new enum
    # First, convert any existing llm_batch_run values to a different type (or handle them)
    op.execute("UPDATE job SET tag = 'LLM_BATCH_RUN' WHERE tag = 'LLM_BATCH_RUN'")
    
    # Step 3: Alter the column to use the new enum type
    op.execute("ALTER TABLE job ALTER COLUMN tag TYPE jobtype_new USING tag::text::jobtype_new")
    
    # Step 4: Drop the old enum and rename the new one
    op.execute("DROP TYPE jobtype")
    op.execute("ALTER TYPE jobtype_new RENAME TO jobtype")
