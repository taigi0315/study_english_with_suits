"""
CRUD operations for LangFlix database models.

This module provides database operations for Media, Expression, and ProcessingJob models.
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from langflix.db.models import Media, Expression, ProcessingJob


class MediaCRUD:
    """CRUD operations for Media model."""
    
    @staticmethod
    def create(db: Session, show_name: str, episode_name: str, language_code: str, 
               subtitle_file_path: str = None, video_file_path: str = None) -> Media:
        """Create new media record."""
        media = Media(
            show_name=show_name,
            episode_name=episode_name,
            language_code=language_code,
            subtitle_file_path=subtitle_file_path,
            video_file_path=video_file_path
        )
        db.add(media)
        db.commit()
        db.refresh(media)
        return media
    
    @staticmethod
    def get_by_id(db: Session, media_id: str) -> Optional[Media]:
        """Get media by ID."""
        return db.query(Media).filter(Media.id == media_id).first()
    
    @staticmethod
    def get_by_show_episode(db: Session, show_name: str, episode_name: str) -> Optional[Media]:
        """Get media by show and episode."""
        return db.query(Media).filter(
            Media.show_name == show_name,
            Media.episode_name == episode_name
        ).first()
    
    @staticmethod
    def update_file_paths(db: Session, media_id: str, subtitle_path: str = None, 
                          video_path: str = None) -> Optional[Media]:
        """Update file paths."""
        media = db.query(Media).filter(Media.id == media_id).first()
        if media:
            if subtitle_path:
                media.subtitle_file_path = subtitle_path
            if video_path:
                media.video_file_path = video_path
            db.commit()
            db.refresh(media)
        return media
    
    @staticmethod
    def list_all(db: Session, skip: int = 0, limit: int = 100) -> List[Media]:
        """List all media with pagination."""
        return db.query(Media).offset(skip).limit(limit).all()


class ExpressionCRUD:
    """CRUD operations for Expression model."""
    
    @staticmethod
    def create_from_analysis(db: Session, media_id: str, analysis_data) -> Expression:
        """Create expression from ExpressionAnalysis data."""
        expression = Expression(
            media_id=media_id,
            expression=analysis_data.expression,
            expression_translation=analysis_data.expression_translation,
            expression_dialogue=analysis_data.expression_dialogue,
            expression_dialogue_translation=analysis_data.expression_dialogue_translation,
            similar_expressions=analysis_data.similar_expressions,
            context_start_time=analysis_data.context_start_time,
            context_end_time=analysis_data.context_end_time,
            scene_type=analysis_data.scene_type,
            context_video_path=analysis_data.context_video_path,
            slide_video_path=analysis_data.slide_video_path
        )
        db.add(expression)
        db.commit()
        db.refresh(expression)
        return expression
    
    @staticmethod
    def create(db: Session, media_id: str, expression: str, expression_translation: str = None,
               expression_dialogue: str = None, expression_dialogue_translation: str = None,
               similar_expressions: List[str] = None, context_start_time: str = None,
               context_end_time: str = None, scene_type: str = None,
               context_video_path: str = None, slide_video_path: str = None) -> Expression:
        """Create new expression record."""
        expr = Expression(
            media_id=media_id,
            expression=expression,
            expression_translation=expression_translation,
            expression_dialogue=expression_dialogue,
            expression_dialogue_translation=expression_dialogue_translation,
            similar_expressions=similar_expressions,
            context_start_time=context_start_time,
            context_end_time=context_end_time,
            scene_type=scene_type,
            context_video_path=context_video_path,
            slide_video_path=slide_video_path
        )
        db.add(expr)
        db.commit()
        db.refresh(expr)
        return expr
    
    @staticmethod
    def get_by_media(db: Session, media_id: str) -> List[Expression]:
        """Get all expressions for a media."""
        return db.query(Expression).filter(Expression.media_id == media_id).all()
    
    @staticmethod
    def get_by_id(db: Session, expression_id: str) -> Optional[Expression]:
        """Get expression by ID."""
        return db.query(Expression).filter(Expression.id == expression_id).first()
    
    @staticmethod
    def search_by_text(db: Session, search_text: str) -> List[Expression]:
        """Search expressions by text."""
        return db.query(Expression).filter(
            Expression.expression.ilike(f"%{search_text}%")
        ).all()
    
    @staticmethod
    def delete_by_media(db: Session, media_id: str) -> int:
        """Delete all expressions for a media."""
        count = db.query(Expression).filter(Expression.media_id == media_id).delete()
        db.commit()
        return count


class ProcessingJobCRUD:
    """CRUD operations for ProcessingJob model."""
    
    @staticmethod
    def create(db: Session, media_id: str) -> ProcessingJob:
        """Create new processing job."""
        job = ProcessingJob(media_id=media_id, status="PENDING")
        db.add(job)
        db.commit()
        db.refresh(job)
        return job
    
    @staticmethod
    def get_by_id(db: Session, job_id: str) -> Optional[ProcessingJob]:
        """Get job by ID."""
        return db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
    
    @staticmethod
    def get_by_media(db: Session, media_id: str) -> List[ProcessingJob]:
        """Get all jobs for a media."""
        return db.query(ProcessingJob).filter(ProcessingJob.media_id == media_id).all()
    
    @staticmethod
    def update_status(db: Session, job_id: str, status: str, progress: int = None, 
                     error_message: str = None) -> Optional[ProcessingJob]:
        """Update job status."""
        job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        if job:
            job.status = status
            if progress is not None:
                job.progress = progress
            if error_message:
                job.error_message = error_message
            if status == "PROCESSING":
                job.started_at = func.now()
            elif status in ["COMPLETED", "FAILED"]:
                job.completed_at = func.now()
            db.commit()
            db.refresh(job)
        return job
    
    @staticmethod
    def get_by_status(db: Session, status: str) -> List[ProcessingJob]:
        """Get jobs by status."""
        return db.query(ProcessingJob).filter(ProcessingJob.status == status).all()
    
    @staticmethod
    def get_active_jobs(db: Session) -> List[ProcessingJob]:
        """Get all active jobs (PENDING or PROCESSING)."""
        return db.query(ProcessingJob).filter(
            ProcessingJob.status.in_(["PENDING", "PROCESSING"])
        ).all()
    
    @staticmethod
    def delete_by_media(db: Session, media_id: str) -> int:
        """Delete all jobs for a media."""
        count = db.query(ProcessingJob).filter(ProcessingJob.media_id == media_id).delete()
        db.commit()
        return count
