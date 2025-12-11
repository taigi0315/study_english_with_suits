# LangFlix Documentation

Welcome to LangFlix - Learn English expressions from TV shows through AI-powered video analysis.

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE](ARCHITECTURE.md) | System design, modules, data flow |
| [API](API.md) | REST API reference |
| [CONFIGURATION](CONFIGURATION.md) | All config options |
| [DEVELOPMENT](DEVELOPMENT.md) | Setup, testing, contributing |
| [DEPLOYMENT](DEPLOYMENT.md) | Docker, TrueNAS deployment |
| [TROUBLESHOOTING_GUIDE](TROUBLESHOOTING_GUIDE.md) | Common issues & solutions |

## 🚀 Quick Start

```bash
# Clone & setup
git clone https://github.com/taigi0315/study_english_with_suits.git
cd study_english_with_suits
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp env.example .env  # Add GEMINI_API_KEY

# Run
make dev-all
```

See [DEVELOPMENT](DEVELOPMENT.md) for detailed setup.

## 🔗 Additional Resources

- [ADR (Architecture Decision Records)](adr/) - Technical decisions history
- [YouTube Setup](YOUTUBE_SETUP_GUIDE_eng.md) - YouTube API integration
- [CI/CD SSH Setup](CI_CD_SSH_SETUP.md) - GitHub Actions deployment