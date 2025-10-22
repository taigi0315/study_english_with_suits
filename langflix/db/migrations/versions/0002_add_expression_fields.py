"""Add expression fields for learning features

Revision ID: 0002_add_expression_fields
Revises: 0001_initial_schema
Create Date: 2025-01-27 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0002_add_expression_fields'
down_revision = '0001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add new fields to expressions table for expression-based learning features."""
    # Add new columns to expressions table
    op.add_column('expressions', sa.Column('difficulty', sa.Integer(), nullable=True))
    op.add_column('expressions', sa.Column('category', sa.String(50), nullable=True))
    op.add_column('expressions', sa.Column('educational_value', sa.Text(), nullable=True))
    op.add_column('expressions', sa.Column('usage_notes', sa.Text(), nullable=True))
    op.add_column('expressions', sa.Column('score', sa.Float(), nullable=True))


def downgrade() -> None:
    """Remove expression learning fields from expressions table."""
    # Remove the added columns
    op.drop_column('expressions', 'score')
    op.drop_column('expressions', 'usage_notes')
    op.drop_column('expressions', 'educational_value')
    op.drop_column('expressions', 'category')
    op.drop_column('expressions', 'difficulty')
