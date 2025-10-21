"""
FastAPI application entry point for LangFlix API.

This module creates and configures the FastAPI application with
all necessary middleware, routes, and exception handlers.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from .routes import health, jobs, files
from .exceptions import APIException, api_exception_handler
from .middleware import LoggingMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="LangFlix API",
        description="Language learning video processing API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add custom middleware
    app.add_middleware(LoggingMiddleware)
    
    # Include routers
    app.include_router(health.router, tags=["health"])
    app.include_router(jobs.router, prefix="/api/v1", tags=["jobs"])
    app.include_router(files.router, prefix="/api/v1", tags=["files"])
    
    # Add exception handlers
    app.add_exception_handler(APIException, api_exception_handler)
    app.add_exception_handler(HTTPException, api_exception_handler)
    
    return app

# Create app instance
app = create_app()

@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info("LangFlix API starting up...")
    # Initialize database connection
    # Initialize storage backends
    logger.info("LangFlix API started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("LangFlix API shutting down...")
    # Cleanup resources
    logger.info("LangFlix API shutdown complete")
