"""
Job management routes for LangFlix API.

This module provides endpoints for creating, monitoring, and retrieving job results.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, UploadFile, File, Form
from typing import List
from uuid import UUID
from datetime import datetime, timezone

from ..models.requests import JobCreateRequest
from ..models.responses import JobStatusResponse, JobExpressionsResponse
from ..dependencies import get_db, get_storage
from ..tasks.processing import process_video_task

router = APIRouter()

@router.post("/jobs", response_model=JobStatusResponse)
async def create_job(
    video_file: UploadFile = File(...),
    subtitle_file: UploadFile = File(...),
    language_code: str = Form(...),
    show_name: str = Form(...),
    episode_name: str = Form(...),
    max_expressions: int = Form(10),
    language_level: str = Form("intermediate"),
    test_mode: bool = Form(False),
    no_shorts: bool = Form(False),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db = Depends(get_db),
    storage = Depends(get_storage)
):
    """Create a new video processing job."""
    try:
        # Validate files
        if not video_file.filename.endswith(('.mp4', '.mkv', '.avi')):
            raise HTTPException(status_code=400, detail="Invalid video file format")
        
        if not subtitle_file.filename.endswith(('.srt', '.vtt')):
            raise HTTPException(status_code=400, detail="Invalid subtitle file format")
        
        # TODO: Create job record in database
        # job = await create_job_record(db, job_config)
        
        # TODO: Start background processing
        # background_tasks.add_task(
        #     process_video_task,
        #     job_id=str(job.id),
        #     video_file=video_file,
        #     subtitle_file=subtitle_file,
        #     config=job_config
        # )
        
        # Mock response for now
        return JobStatusResponse(
            job_id="mock-job-id",
            status="PENDING",
            progress=0,
            created_at=datetime.now(timezone.utc)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create job: {str(e)}")

@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str, db = Depends(get_db)):
    """Get job status by ID."""
    # TODO: Get job from database
    # job = await get_job_by_id(db, job_id)
    # if not job:
    #     raise HTTPException(status_code=404, detail="Job not found")
    
    # Mock response for now
    return JobStatusResponse(
        job_id=str(job_id),
        status="PROCESSING",
        progress=75,
        created_at=datetime.now(timezone.utc),
        started_at=datetime.now(timezone.utc)
    )

@router.get("/jobs/{job_id}/expressions", response_model=JobExpressionsResponse)
async def get_job_expressions(job_id: str, db = Depends(get_db)):
    """Get expressions for a completed job."""
    # TODO: Get job from database
    # job = await get_job_by_id(db, job_id)
    # if not job:
    #     raise HTTPException(status_code=404, detail="Job not found")
    
    # if job.status != "COMPLETED":
    #     raise HTTPException(status_code=400, detail="Job not completed yet")
    
    # TODO: Get expressions from database
    # expressions = await get_expressions_by_job(db, job_id)
    
    # Mock response for now
    return JobExpressionsResponse(
        job_id=str(job_id),
        expressions=[],
        total=0
    )

@router.get("/jobs", response_model=List[JobStatusResponse])
async def list_jobs(
    status: str = None,
    limit: int = 50,
    offset: int = 0,
    db = Depends(get_db)
):
    """List jobs with optional filtering."""
    # TODO: Get jobs from database
    # jobs = await list_jobs_from_db(db, status, limit, offset)
    
    # Mock response for now
    return []
