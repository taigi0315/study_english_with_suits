# ============================================================================
# LangFlix Production Dockerfile (Multi-stage Build)
# ============================================================================
# 
# This Dockerfile creates optimized production images for LangFlix.
# Multi-stage build reduces final image size while maintaining functionality.
#
# Build targets:
#   - builder: Dependencies installation stage
#   - runtime: Base runtime image
#   - api: FastAPI server image (default)
#
# Usage:
#   docker build -t langflix:latest .
#   docker build --target api -t langflix:api .
#
# ============================================================================

# ----------------------------------------------------------------------------
# Stage 1: Builder - Install dependencies and build application
# ----------------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Create virtual environment for dependency isolation
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install build tools
RUN pip install --upgrade pip setuptools wheel

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# ----------------------------------------------------------------------------
# Stage 2: Runtime - Lightweight production image
# ----------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

# Install runtime dependencies and Korean fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    fonts-noto-cjk \
    fonts-noto-cjk-extra \
    fontconfig \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -fv

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user for security
RUN useradd -m -u 1000 -s /bin/bash langflix && \
    mkdir -p /app /data/output /data/logs /data/assets /app/cache && \
    chown -R langflix:langflix /app /data

WORKDIR /app
USER langflix

# Copy application code
COPY --chown=langflix:langflix . .

# Expose ports
EXPOSE 8000 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# ----------------------------------------------------------------------------
# Stage 3: API - FastAPI server (default)
# ----------------------------------------------------------------------------
FROM runtime AS api

# Default command: Start FastAPI server
CMD ["python", "-m", "langflix.api.main"]

# ----------------------------------------------------------------------------
# Stage 4: UI - Flask-based management dashboard
# ----------------------------------------------------------------------------
FROM runtime AS ui

ENV LANGFLIX_UI_PORT=5000
EXPOSE 5000

# Default command: Start Flask web UI
CMD ["python", "-m", "langflix.youtube.web_ui"]

