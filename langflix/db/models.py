"""
Database models for LangFlix.

This module defines SQLAlchemy models for storing metadata and structured data.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey, CheckConstraint, func, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Media(Base):
    """Media table for storing episode/show metadata."""
    
    __tablename__ = "media"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    show_name = Column(String(255), nullable=False)
    episode_name = Column(String(255), nullable=False)
    language_code = Column(String(10), nullable=False)
    subtitle_file_path = Column(Text)  # Reference to storage backend
    video_file_path = Column(Text)     # Reference to storage backend
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    expressions = relationship("Expression", back_populates="media", cascade="all, delete-orphan")
    processing_jobs = relationship("ProcessingJob", back_populates="media", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Media(id={self.id}, show='{self.show_name}', episode='{self.episode_name}')>"


class Expression(Base):
    """Expression table for storing individual expressions and their analysis data."""
    
    __tablename__ = "expressions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    media_id = Column(UUID(as_uuid=True), ForeignKey("media.id", ondelete="CASCADE"), nullable=False)
    expression = Column(Text, nullable=False)
    expression_translation = Column(Text)
    expression_dialogue = Column(Text)
    expression_dialogue_translation = Column(Text)
    similar_expressions = Column(JSONB)  # Array of similar expressions
    context_start_time = Column(String(20))  # e.g., "00:01:23,456"
    context_end_time = Column(String(20))    # e.g., "00:01:25,789"
    scene_type = Column(String(50))          # e.g., "dialogue", "action"
    context_video_path = Column(Text)        # Reference to storage backend
    slide_video_path = Column(Text)         # Reference to storage backend
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # New fields for expression-based learning
    difficulty = Column(Integer)              # 1-10 difficulty level
    category = Column(String(50))             # idiom, slang, formal, etc.
    educational_value = Column(Text)          # Educational value explanation
    usage_notes = Column(Text)                # Additional usage context
    score = Column(Float)                     # Ranking score for selection
    
    # Relationships
    media = relationship("Media", back_populates="expressions")
    
    def __repr__(self):
        return f"<Expression(id={self.id}, expression='{self.expression[:50]}...')>"


class ProcessingJob(Base):
    """ProcessingJob table for tracking asynchronous processing jobs."""
    
    __tablename__ = "processing_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    media_id = Column(UUID(as_uuid=True), ForeignKey("media.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), nullable=False, default="PENDING")  # PENDING, PROCESSING, COMPLETED, FAILED
    progress = Column(Integer, default=0)
    error_message = Column(Text)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Constraints
    __table_args__ = (
        CheckConstraint("progress >= 0 AND progress <= 100", name="check_progress_range"),
    )
    
    # Relationships
    media = relationship("Media", back_populates="processing_jobs")
    
    def __repr__(self):
        return f"<ProcessingJob(id={self.id}, status='{self.status}', progress={self.progress})>"
