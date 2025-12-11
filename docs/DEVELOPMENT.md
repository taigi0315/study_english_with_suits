# Development Guide

## Quick Start

### Prerequisites
- Python 3.9+
- FFmpeg installed
- Google Gemini API key

### Setup

```bash
# Clone repository
git clone https://github.com/taigi0315/study_english_with_suits.git
cd study_english_with_suits

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp env.example .env
# Edit .env and add your GEMINI_API_KEY

# Copy configuration
cp config/config.example.yaml config/config.yaml
```

---

## Running the Application

### Development Mode
```bash
# Start full environment (API + Frontend)
make dev-all

# Or start services separately
make dev-backend   # FastAPI on port 8000
make dev-frontend  # Flask on port 5000
```

### CLI Mode
```bash
# Test mode (2 expressions only)
python -m langflix.main \
  --subtitle "assets/media/test/test.srt" \
  --test-mode \
  --max-expressions 2

# Full processing
python -m langflix.main \
  --subtitle "assets/media/Suits/Suits.S01E01.srt" \
  --language-code ko \
  --verbose
```

---

## Testing

### Run All Tests
```bash
make test
# or
python scripts/run_tests.py all
```

### Test Types
```bash
# Unit tests
python -m pytest tests/unit/ -v

# Integration tests
python -m pytest tests/integration/ -v

# API tests
python -m pytest tests/api/ -v
```

---

## Make Commands

| Command | Description |
|---------|-------------|
| `make dev` | Start development environment |
| `make test` | Run all tests |
| `make docker-up` | Start Docker services |
| `make docker-down` | Stop Docker services |
| `make status` | Check service status |
| `make stop-all` | Stop all services |
| `make help` | Show all commands |

---

## Project Structure

```
langflix/
├── langflix/        # Main application package
├── tests/           # Test suite
├── config/          # Configuration files
├── assets/          # Media and fonts
├── deploy/          # Docker deployment
├── scripts/         # Utility scripts
└── docs/            # Documentation
```

---

## Troubleshooting

### Common Issues

**FFmpeg not found:**
```bash
# macOS
brew install ffmpeg

# Ubuntu
sudo apt install ffmpeg
```

**API key issues:**
```bash
# Verify key is set
echo $GEMINI_API_KEY

# Or check .env file
cat .env | grep GEMINI
```

**Port conflicts:**
```bash
# Kill processes on ports
make stop-all-force
```

See [TROUBLESHOOTING_GUIDE.md](TROUBLESHOOTING_GUIDE.md) for more solutions.
