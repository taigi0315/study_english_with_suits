.PHONY: all setup clean test api dev install

# Default target
all: setup

# Setup virtual environment and install dependencies
setup: venv install
	@echo "✅ LangFlix setup complete!"
	@echo "🚀 Run 'make api' to start the API server"

# Create virtual environment
venv:
	@echo "Creating virtual environment..."
	python3 -m venv venv
	@echo "Virtual environment created."

# Install dependencies
install: venv
	@echo "Installing dependencies..."
	. venv/bin/activate && pip install -r requirements.txt
	@echo "Dependencies installed."

# Start API server
api: venv
	@echo "🚀 Starting LangFlix API server..."
	. venv/bin/activate && uvicorn langflix.api.main:app --host 127.0.0.1 --port 8000 --reload

# Development mode with hot reload
dev: venv
	@echo "🔧 Starting LangFlix API in development mode..."
	. venv/bin/activate && uvicorn langflix.api.main:app --host 127.0.0.1 --port 8000 --reload --log-level debug

# Run tests
test: venv
	@echo "Running tests..."
	. venv/bin/activate && python -m pytest tests/ -v

# Run specific test categories
test-unit: venv
	@echo "Running unit tests..."
	. venv/bin/activate && python -m pytest tests/unit/ -v

test-functional: venv
	@echo "Running functional tests..."
	. venv/bin/activate && python -m pytest tests/functional/ -v

test-api: venv
	@echo "Running API tests..."
	. venv/bin/activate && python -m pytest tests/api/ -v

# Database operations
db-migrate: venv
	@echo "Running database migrations..."
	. venv/bin/activate && alembic upgrade head

db-reset: venv
	@echo "Resetting database..."
	. venv/bin/activate && alembic downgrade base && alembic upgrade head

# Clean up
clean:
	@echo "Cleaning up..."
	rm -rf venv
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf output
	rm -rf test_output
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleanup complete."

# Help
help:
	@echo "LangFlix Makefile Commands:"
	@echo "  make setup     - Setup virtual environment and install dependencies"
	@echo "  make api       - Start API server"
	@echo "  make dev       - Start API server in development mode"
	@echo "  make test      - Run all tests"
	@echo "  make test-unit - Run unit tests only"
	@echo "  make test-functional - Run functional tests only"
	@echo "  make test-api  - Run API tests only"
	@echo "  make db-migrate - Run database migrations"
	@echo "  make db-reset  - Reset database"
	@echo "  make clean     - Clean up generated files"
	@echo "  make help      - Show this help message"
