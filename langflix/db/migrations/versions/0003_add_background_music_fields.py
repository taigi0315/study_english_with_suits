"""Add background_music fields to expressions

Revision ID: 0003_add_background_music_fields
Revises: 0002_add_expression_fields
Create Date: 2025-01-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0003_add_background_music_fields'
down_revision = '0002_add_expression_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add background_music_id and background_music_reasoning fields to expressions table."""
    # Add new columns to expressions table
    op.add_column('expressions', sa.Column('background_music_id', sa.String(50), nullable=True))
    op.add_column('expressions', sa.Column('background_music_reasoning', sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove background music fields from expressions table."""
    # Remove the added columns
    op.drop_column('expressions', 'background_music_reasoning')
    op.drop_column('expressions', 'background_music_id')
