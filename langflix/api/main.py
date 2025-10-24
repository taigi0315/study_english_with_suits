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
    # TODO: Initialize database connection
    # TODO: Initialize storage backends
    logger.info("LangFlix API started successfully")
    
    yield
    
    # Shutdown
    logger.info("LangFlix API shutting down...")
    # TODO: Cleanup resources
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
    
    # Add UI endpoint
    @app.get("/", response_class=HTMLResponse)
    async def root():
        """Serve the main UI."""
        template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "templates", "fastapi_ui.html")
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                return HTMLResponse(content=f.read())
        else:
            return HTMLResponse(content="<h1>LangFlix API</h1><p><a href='/docs'>API Documentation</a></p>")
    
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
