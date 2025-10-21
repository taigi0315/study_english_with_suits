"""Initial schema

Revision ID: 0001
Revises: 
Create Date: 2025-10-21 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create media table
    op.create_table('media',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('show_name', sa.String(length=255), nullable=False),
        sa.Column('episode_name', sa.String(length=255), nullable=False),
        sa.Column('language_code', sa.String(length=10), nullable=False),
        sa.Column('subtitle_file_path', sa.Text(), nullable=True),
        sa.Column('video_file_path', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_media_show_episode', 'media', ['show_name', 'episode_name'])
    op.create_index('idx_media_language', 'media', ['language_code'])
    
    # Create expressions table
    op.create_table('expressions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('media_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('expression', sa.Text(), nullable=False),
        sa.Column('expression_translation', sa.Text(), nullable=True),
        sa.Column('expression_dialogue', sa.Text(), nullable=True),
        sa.Column('expression_dialogue_translation', sa.Text(), nullable=True),
        sa.Column('similar_expressions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('context_start_time', sa.String(length=20), nullable=True),
        sa.Column('context_end_time', sa.String(length=20), nullable=True),
        sa.Column('scene_type', sa.String(length=50), nullable=True),
        sa.Column('context_video_path', sa.Text(), nullable=True),
        sa.Column('slide_video_path', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['media_id'], ['media.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_expressions_media', 'expressions', ['media_id'])
    op.create_index('idx_expressions_text', 'expressions', [sa.text("to_tsvector('english', expression)")], postgresql_using='gin')
    
    # Create processing_jobs table
    op.create_table('processing_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('media_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('progress', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['media_id'], ['media.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('progress >= 0 AND progress <= 100', name='check_progress_range')
    )
    op.create_index('idx_jobs_status', 'processing_jobs', ['status'])
    op.create_index('idx_jobs_media', 'processing_jobs', ['media_id'])


def downgrade() -> None:
    op.drop_table('processing_jobs')
    op.drop_table('expressions')
    op.drop_table('media')
