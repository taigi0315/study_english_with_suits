# LangFlix Documentation

Welcome to LangFlix - Learn English expressions from TV shows through AI-powered video analysis and generation.

## 📚 Documentation Overview

### Getting Started
- **[Quick Start Guide](QUICK_START_GUIDE.md)** - Get up and running in 5 minutes
- **[Setup Guide](../SETUP_GUIDE.md)** - Complete installation and setup instructions

### User Guides
- **[CLI Reference](CLI_REFERENCE.md)** - Command-line interface usage and options
- **[Configuration Guide](CONFIGURATION_GUIDE.md)** - Advanced configuration and customization
- **[API Reference](API_REFERENCE.md)** - Web API usage and integration

### Module Documentation

#### Core Modules
- **[Core Module](core/README_eng.md)** - Video editing and pipeline logic (`video_editor.py`, `expression_analyzer.py`)
- **[Media Module](media/README_eng.md)** - FFmpeg utilities and media processing (`ffmpeg_utils.py`)
- **[Services Module](services/README_eng.md)** - Service layer classes (`VideoPipelineService`)
- **[API Module](api/README_eng.md)** - FastAPI routes and endpoints

#### Storage & Configuration
- **[Storage Module](storage/README_eng.md)** - Storage abstraction layer (Local, GCS)
- **[Config Module](config/README_eng.md)** - Configuration management and font utilities
- **[Database Module](db/README_eng.md)** - Database models and CRUD operations

#### Media Processing
- **[Audio Module](audio/README_eng.md)** - Audio optimization and extraction
- **[TTS Module](tts/)** - Text-to-speech integration (Gemini, LemonFox)
- **[Video Module](video/)** - Video enhancement utilities
- **[Subtitles Module](subtitles/)** - Subtitle overlay and processing

#### Services & Utilities
- **[Monitoring Module](monitoring/README_eng.md)** - Health checks and performance monitoring
- **[Tasks Module](tasks/)** - Background task processing (Celery)
- **[Slides Module](slides/)** - Educational slide generation
- **[YouTube Module](youtube/README_eng.md)** - YouTube upload and scheduling
- **[Utils Module](utils/)** - Utility functions
  - [TempFileManager](utils/temp_file_manager_eng.md) - Temporary file management
  - [Filename Utils](utils/filename_utils_eng.md) - Filename sanitization

#### Deployment
- **[CI/CD SSH Setup](CI_CD_SSH_SETUP.md)** - TrueNAS deployment configuration

### Troubleshooting
- **[Troubleshooting Guide](TROUBLESHOOTING_GUIDE.md)** - Common issues and solutions

### Additional Resources
- **[User Manual (Korean)](ko/USER_MANUAL_KOR.md)** - 한국어 사용자 매뉴얼
- **[API Reference (Korean)](ko/API_REFERENCE_KOR.md)** - 한국어 API 문서
- **[Performance Guide](en/PERFORMANCE.md)** - Performance optimization tips
- **[Deployment Guide](en/DEPLOYMENT.md)** - Production deployment instructions

---

## 🚀 Quick Start

### Recent Improvements (2025-01-30)

**Code Quality & Architecture:**
- **TICKET-001-extract-pipeline-logic:** Unified `VideoPipelineService` - eliminates 450+ lines of duplicate code between API and CLI
- **TICKET-002:** Standardized `TempFileManager` - automatic temp file cleanup prevents disk leaks
- **TICKET-004:** Consolidated `filename_utils` - single source of truth for filename sanitization (7+ duplicates removed)
- **TICKET-005:** Error handler integration - structured error reporting with automatic retry

**Media Pipeline:**
- **TICKET-001:** Demuxer-first approach for reliable audio preservation
- **TICKET-001:** Standardized layouts (hstack for long-form, vstack for short-form)
- **TICKET-001:** Fixed A-V sync issues with copy mode concatenation
- See [ADR-015](adr/ADR-015-ffmpeg-pipeline-standardization_eng.md) for design details

### Installation (5 minutes)

```bash
# Clone repository
git clone https://github.com/taigi0315/study_english_with_suits.git
cd study_english_with_suits

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp env.example .env
# Edit .env and add your Gemini API key

# Copy configuration
cp config.example.yaml config.yaml
```

### First Run

```bash
# Test mode (2 expressions only)
python -m langflix.main \
  --subtitle "assets/media/test/test.srt" \
  --test-mode \
  --max-expressions 2 \
  --verbose
```

### Full Processing

```bash
# Process complete episode
python -m langflix.main \
  --subtitle "assets/media/Suits/Suits.S01E01.srt" \
  --language-code ko \
  --language-level intermediate \
  --verbose
```

---

## 🎯 What LangFlix Does

LangFlix analyzes TV show subtitles to extract educational English expressions and generates learning videos with:

- **Context Videos**: Original video clips with subtitles
- **Educational Slides**: Learning materials with translations
- **Short Videos**: Social media-ready 9:16 format videos
- **Metadata**: Structured expression data for further analysis

### Supported Features

- ✅ **Multi-language Support**: Korean, Japanese, Chinese, Spanish, French
- ✅ **Difficulty Levels**: Beginner, Intermediate, Advanced
- ✅ **Video Formats**: MP4, MKV, AVI support
- ✅ **TTS Integration**: Text-to-speech for pronunciation
- ✅ **YouTube Integration**: Automated upload and scheduling
- ✅ **API Access**: RESTful API for integration
- ✅ **Database Storage**: PostgreSQL integration for data persistence

---

## 📖 Documentation Structure

### Core Documentation

| Document | Description | Audience |
|----------|-------------|----------|
| [Quick Start Guide](QUICK_START_GUIDE.md) | Get started in 5 minutes | New users |
| [CLI Reference](CLI_REFERENCE.md) | Command-line usage | CLI users |
| [Configuration Guide](CONFIGURATION_GUIDE.md) | Advanced configuration | Power users |
| [API Reference](API_REFERENCE.md) | Web API usage | Developers |
| [Troubleshooting Guide](TROUBLESHOOTING_GUIDE.md) | Problem solving | All users |

### Specialized Documentation

| Document | Description | Audience |
|----------|-------------|----------|
| [Performance Guide](en/PERFORMANCE.md) | Optimization tips | Advanced users |
| [Deployment Guide](en/DEPLOYMENT.md) | Production setup | DevOps |
| [YouTube Integration](en/YOUTUBE_INTEGRATION.md) | YouTube automation | Content creators |

### Localized Documentation

| Document | Description | Audience |
|----------|-------------|----------|
| [User Manual (Korean)](ko/USER_MANUAL_KOR.md) | 한국어 사용자 매뉴얼 | Korean users |
| [API Reference (Korean)](ko/API_REFERENCE_KOR.md) | 한국어 API 문서 | Korean developers |
| [Troubleshooting (Korean)](ko/TROUBLESHOOTING_KOR.md) | 한국어 문제 해결 가이드 | Korean users |

---

## 🛠️ Development Resources

### Architecture Documentation

- **[System Design](system_design_and_development_plan.md)** - Overall system architecture
- **[Development Diary](development_diary.md)** - Development progress and decisions
- **[Phase Summaries](PHASE_1_SUMMARY.md)** - Development phase documentation

### Technical References

- **[ADR (Architecture Decision Records)](adr/)** - Technical decision documentation
- **[Migration Strategy](adr/ADR-012-migration-strategy.md)** - Database migration planning
- **[Service Architecture](adr/ADR-009-service-architecture-foundation.md)** - Service design principles

---

## 🔧 Quick Commands

### Essential Commands

```bash
# Basic processing
python -m langflix.main --subtitle "file.srt"

# Test mode
python -m langflix.main --subtitle "file.srt" --test-mode

# With options
python -m langflix.main \
  --subtitle "file.srt" \
  --language-code ko \
  --language-level intermediate \
  --max-expressions 5
```

### Development Commands

```bash
# Start development environment
make dev

# Start with Docker
make docker-up

# Run tests
make test

# Check status
make status
```

### API Commands

```bash
# Start API server
uvicorn langflix.api.main:app --reload

# Test API
curl http://localhost:8000/health

# View API docs
open http://localhost:8000/docs
```

---

## 🌐 Access Points

- **Frontend UI**: http://localhost:5000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Database**: localhost:5432
- **Redis**: localhost:6379

---

## 📞 Support

### Getting Help

1. **Check the documentation** - Start with the relevant guide
2. **Search existing issues** - Look for similar problems
3. **Run diagnostics** - Use built-in diagnostic tools
4. **Report new issues** - Provide detailed information

### Community Resources

- **GitHub Issues**: Report bugs and request features
- **Documentation**: Comprehensive guides and references
- **Examples**: Sample configurations and workflows

### Emergency Commands

```bash
# Kill stuck processes
pkill -f langflix

# Clear cache
rm -rf cache/

# Reset database
alembic downgrade base && alembic upgrade head

# Check system health
python -m langflix.diagnostics
```

---

## 📝 Contributing

### Documentation Contributions

1. **Fork the repository**
2. **Create a feature branch**
3. **Make your changes**
4. **Submit a pull request**

### Documentation Standards

- Use clear, concise language
- Include code examples
- Provide both English and Korean versions when appropriate
- Follow the existing documentation structure

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.

---

## 🔗 Links

- **GitHub Repository**: https://github.com/taigi0315/study_english_with_suits
- **Documentation**: https://github.com/taigi0315/study_english_with_suits/tree/main/docs
- **Issues**: https://github.com/taigi0315/study_english_with_suits/issues
- **Discussions**: https://github.com/taigi0315/study_english_with_suits/discussions

---

**Last Updated**: 2025-01-30  
**Version**: 1.0.0  
**Maintainer**: LangFlix Development Team