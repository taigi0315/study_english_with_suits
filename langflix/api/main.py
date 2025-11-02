from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
import os

from .routes import health, jobs, files
from .exceptions import APIException, api_exception_handler
from .middleware import LoggingMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("LangFlix API starting up...")
    
    # Initialize database connection pool if enabled
    try:
        from langflix import settings
        if settings.get_database_enabled():
            from langflix.api.dependencies import db_manager
            db_manager.initialize()
            logger.info("✅ Database connection pool initialized")
        else:
            logger.info("ℹ️ Database disabled (file-only mode)")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
    
    # Initialize and cleanup Redis on startup
    try:
        from langflix.core.redis_client import get_redis_job_manager
        redis_manager = get_redis_job_manager()
        
        # Cleanup expired and stale jobs on startup
        expired_count = redis_manager.cleanup_expired_jobs()
        stale_count = redis_manager.cleanup_stale_jobs()
        
        logger.info(f"✅ Redis startup cleanup: {expired_count} expired, {stale_count} stale jobs removed")
        
        # Test Redis health
        health = redis_manager.health_check()
        if health["status"] == "healthy":
            logger.info(f"✅ Redis connected: {health['active_jobs']} active jobs")
        else:
            logger.warning(f"⚠️ Redis health check failed: {health.get('error', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"❌ Redis initialization failed: {e}")
    
    logger.info("LangFlix API started successfully")
    
    yield
    
    # Shutdown
    logger.info("LangFlix API shutting down...")
    
    # Close database connections
    try:
        from langflix import settings
        if settings.get_database_enabled():
            from langflix.api.dependencies import db_manager
            db_manager.close()
            logger.info("✅ Database connections closed")
    except Exception as e:
        logger.error(f"❌ Database cleanup failed: {e}")
    
    logger.info("LangFlix API shutdown complete")

def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="LangFlix API",
        description="Language learning video processing API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )
    
    # Note: File size limits are handled by uvicorn configuration
    
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
    
    # Serve static files from output directory (for local development)
    output_dir = "output"
    if os.path.exists(output_dir):
        app.mount("/output", StaticFiles(directory=output_dir), name="output")
    
    # Include routers
    app.include_router(health.router, tags=["health"])
    app.include_router(jobs.router, prefix="/api/v1", tags=["jobs"])
    app.include_router(files.router, prefix="/api/v1", tags=["files"])
    
    # API-only endpoint (no UI)
    @app.get("/")
    async def root():
        """API root endpoint."""
        return {
            "message": "LangFlix API",
            "version": "1.0.0",
            "docs": "/docs",
            "redoc": "/redoc"
        }
    
    # Add local development endpoints
    @app.get("/local/status")
    async def local_status():
        """Local development status endpoint."""
        return {
            "mode": "local_development",
            "output_directory": output_dir,
            "storage_backend": "local",
            "api_docs": "/docs",
            "output_files": "/output/"
        }
    
    # Register exception handlers
    app.add_exception_handler(APIException, api_exception_handler)
    app.add_exception_handler(HTTPException, api_exception_handler)

    return app

# Create app instance
app = create_app()

# Allow running with: python -m langflix.api.main
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("langflix.api.main:app", host="127.0.0.1", port=8000, reload=True)
