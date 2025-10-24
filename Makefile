.PHONY: all setup clean dev dev-backend dev-frontend dev-all dev-parallel docker-up docker-down docker-logs stop-all stop-all-force restart

all: setup

setup: venv
	@echo "Installing dependencies..."
	. venv/bin/activate && pip install -r requirements.txt
	@echo "Setup complete."

venv:
	@echo "Creating virtual environment..."
	python3 -m venv venv
	@echo "Virtual environment created."

download_transcripts: venv
	. venv/bin/activate && python download_transcripts.py

clean:
	@echo "Cleaning up..."
	rm -rf venv
	rm -rf Suits_Transcripts
	rm -rf output
	rm -rf cache
	rm -f langflix.log
	@echo "Cleanup complete."

# Development commands
dev: dev-all

dev-backend:
	@echo "🚀 Starting FastAPI Backend Server..."
	. venv/bin/activate && python -m langflix.api.main

dev-frontend:
	@echo "🌐 Starting Flask Frontend Server..."
	. venv/bin/activate && python -m langflix.youtube.web_ui

dev-all:
	@echo "🎬 Starting Full LangFlix Development Environment..."
	@echo "📋 Starting services in background..."
	@echo "   - FastAPI Backend (Port 8000)"
	@echo "   - Flask Frontend (Port 5000)"
	@echo ""
	@echo "🌐 Access points:"
	@echo "   - Frontend UI: http://localhost:5000"
	@echo "   - Backend API: http://localhost:8000"
	@echo "   - API Docs: http://localhost:8000/docs"
	@echo ""
	@echo "💡 Use 'make docker-up' to start database and cache services"
	@echo "💡 Use 'make dev-parallel' to start both services in parallel"
	@echo "💡 Press Ctrl+C to stop all services"
	@echo ""
	@echo "Starting services sequentially (use dev-parallel for parallel execution)..."
	@echo "Starting FastAPI Backend..."
	@echo "Press Ctrl+C to stop backend and continue to frontend"
	. venv/bin/activate && python -m langflix.api.main &
	@sleep 3
	@echo "Starting Flask Frontend..."
	. venv/bin/activate && python -m langflix.youtube.web_ui

dev-parallel:
	@echo "🎬 Starting LangFlix Services in Parallel..."
	@echo "📋 Starting services:"
	@echo "   - FastAPI Backend (Port 8000)"
	@echo "   - Flask Frontend (Port 5000)"
	@echo ""
	@echo "🌐 Access points:"
	@echo "   - Frontend UI: http://localhost:5000"
	@echo "   - Backend API: http://localhost:8000"
	@echo "   - API Docs: http://localhost:8000/docs"
	@echo ""
	@echo "Starting services in parallel..."
	@echo "Press Ctrl+C to stop all services"
	@trap 'kill $$(jobs -p)' EXIT; \
	. venv/bin/activate && python -m langflix.api.main & \
	. venv/bin/activate && python -m langflix.youtube.web_ui & \
	wait

# Docker commands
docker-up:
	@echo "🐳 Starting LangFlix with Docker Compose..."
	@echo "📋 Starting services:"
	@echo "   - PostgreSQL Database"
	@echo "   - Redis Cache"
	@echo "   - Celery Worker"
	@echo "   - Celery Beat Scheduler"
	@echo ""
	docker-compose -f docker-compose.dev.yml up -d
	@echo "✅ Services started successfully!"
	@echo ""
	@echo "🌐 Access points:"
	@echo "   - Database: localhost:5432"
	@echo "   - Redis: localhost:6379"
	@echo ""
	@echo "💡 Use 'make docker-logs' to view logs"
	@echo "💡 Use 'make docker-down' to stop services"

docker-down:
	@echo "🛑 Stopping LangFlix Docker services..."
	docker-compose -f docker-compose.dev.yml down
	@echo "✅ Services stopped successfully!"

docker-logs:
	@echo "📋 Viewing LangFlix Docker logs..."
	docker-compose -f docker-compose.dev.yml logs -f

docker-restart:
	@echo "🔄 Restarting LangFlix Docker services..."
	docker-compose -f docker-compose.dev.yml restart
	@echo "✅ Services restarted successfully!"

# Database commands
db-migrate:
	@echo "📊 Running database migrations..."
	. venv/bin/activate && alembic upgrade head
	@echo "✅ Database migrations completed!"

db-reset:
	@echo "🗑️ Resetting database..."
	. venv/bin/activate && alembic downgrade base && alembic upgrade head
	@echo "✅ Database reset completed!"

# Test commands
test:
	@echo "🧪 Running tests..."
	. venv/bin/activate && python run_tests.py

test-api:
	@echo "🧪 Running API tests..."
	. venv/bin/activate && python -m pytest tests/api/ -v

test-unit:
	@echo "🧪 Running unit tests..."
	. venv/bin/activate && python -m pytest tests/unit/ -v

# Utility commands
logs:
	@echo "📋 Viewing LangFlix logs..."
	tail -f langflix.log

status:
	@echo "📊 Checking service status..."
	@echo "Docker services:"
	@docker-compose -f docker-compose.dev.yml ps 2>/dev/null || echo "Docker services not running"
	@echo ""
	@echo "Python processes:"
	@ps aux | grep -E "(langflix|uvicorn)" | grep -v grep || echo "No Python services running"
	@echo ""
	@echo "Port usage:"
	@lsof -i :8000 2>/dev/null || echo "Port 8000 (API) is free"
	@lsof -i :5000 2>/dev/null || echo "Port 5000 (Frontend) is free"
	@lsof -i :5432 2>/dev/null || echo "Port 5432 (PostgreSQL) is free"
	@lsof -i :6379 2>/dev/null || echo "Port 6379 (Redis) is free"

stop-all:
	@echo "🛑 Stopping all LangFlix services..."
	@echo "Attempting graceful shutdown..."
	@pkill -f "python -m langflix.api.main" 2>/dev/null || echo "No API server running"
	@pkill -f "python -m langflix.youtube.web_ui" 2>/dev/null || echo "No frontend server running"
	@pkill -f "uvicorn" 2>/dev/null || echo "No uvicorn processes running"
	@sleep 2
	@echo "Checking for remaining processes..."
	@if pgrep -f "langflix" > /dev/null; then \
		echo "⚠️  Some processes still running, use 'make stop-all-force' for force kill"; \
		pgrep -f "langflix" | xargs ps -p; \
	else \
		echo "✅ All services stopped gracefully"; \
	fi

stop-all-force:
	@echo "🛑 Force stopping all LangFlix services..."
	@echo "Killing all LangFlix related processes..."
	@pkill -9 -f "langflix.api.main" 2>/dev/null || echo "No API server running"
	@pkill -9 -f "langflix.youtube.web_ui" 2>/dev/null || echo "No frontend server running"
	@pkill -9 -f "uvicorn.*langflix" 2>/dev/null || echo "No uvicorn processes running"
	@echo "Killing processes on ports 8000 and 5000..."
	@lsof -ti:8000 | xargs kill -9 2>/dev/null || echo "No processes on port 8000"
	@lsof -ti:5000 | xargs kill -9 2>/dev/null || echo "No processes on port 5000"
	@echo "✅ All services force stopped"

restart:
	@echo "🔄 Restarting LangFlix services..."
	@$(MAKE) stop-all
	@sleep 2
	@$(MAKE) dev-parallel

help:
	@echo "🎬 LangFlix Make Commands"
	@echo ""
	@echo "Setup Commands:"
	@echo "  make setup          - Install dependencies and setup environment"
	@echo "  make venv           - Create virtual environment"
	@echo "  make clean          - Clean up temporary files"
	@echo ""
	@echo "Development Commands:"
	@echo "  make dev            - Start full development environment"
	@echo "  make dev-backend    - Start FastAPI backend only"
	@echo "  make dev-frontend   - Start Flask frontend only"
	@echo "  make dev-all        - Start all services sequentially"
	@echo "  make dev-parallel   - Start all services in parallel"
	@echo ""
	@echo "Docker Commands:"
	@echo "  make docker-up      - Start all services with Docker"
	@echo "  make docker-down    - Stop all Docker services"
	@echo "  make docker-logs    - View Docker service logs"
	@echo "  make docker-restart - Restart all Docker services"
	@echo ""
	@echo "Database Commands:"
	@echo "  make db-migrate     - Run database migrations"
	@echo "  make db-reset       - Reset database to clean state"
	@echo ""
	@echo "Test Commands:"
	@echo "  make test           - Run all tests"
	@echo "  make test-api       - Run API tests only"
	@echo "  make test-unit      - Run unit tests only"
	@echo ""
	@echo "Utility Commands:"
	@echo "  make logs           - View application logs"
	@echo "  make status         - Check service status"
	@echo "  make stop-all       - Stop all running services (graceful)"
	@echo "  make stop-all-force - Force stop all services (SIGKILL)"
	@echo "  make restart        - Restart all services"
	@echo "  make help           - Show this help message"
	@echo ""
	@echo "🌐 Access Points:"
	@echo "  Frontend UI: http://localhost:5000"
	@echo "  Backend API: http://localhost:8000"
	@echo "  API Docs: http://localhost:8000/docs"

# Legacy command for backward compatibility
venv_init:
	source .venv/bin/activate
