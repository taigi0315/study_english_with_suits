# LangFlix Documentation

> **Version 2.0** - Dual-Language Architecture

## Quick Links

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | V2 system design with dual-language subtitle support |
| [CONFIGURATION.md](./CONFIGURATION.md) | Configuration settings for V2 features |
| [FEATURE_GLOSSARY.md](./FEATURE_GLOSSARY.md) | Standard terminology for V2 components |
| [v1/](./v1/) | Archived V1 documentation |

## What's New in V2

### Dual-Language Subtitle Architecture
V2 introduces a fundamentally new approach to language learning content:

| Feature | V1 | V2 |
|---------|----|----|
| Subtitle Source | Single file, LLM translates | Dual files from Netflix |
| Translation | LLM generates on-the-fly | Pre-existing professional translations |
| Token Usage | ~1000 tokens/expression | ~300 tokens/expression (70% reduction) |
| Font Support | Single language | Dual-font for mixed content |

### Key V2 Components

1. **DualSubtitleService** - Loads and aligns source + target subtitle pairs
2. **V2ContentAnalyzer** - Index-based content selection (no translation)
3. **Netflix Folder Detection** - Auto-discovers subtitle files from Netflix downloads
4. **Dual-Font Rendering** - Correct fonts for Korean←→Spanish, etc.

## Getting Started

```bash
# Enable V2 mode in config
dual_language:
  enabled: true
  source_language: "English"
  target_language: "Korean"
```

## Directory Structure

```
docs/
├── README.md           # This file
├── ARCHITECTURE.md     # V2 system design
├── CONFIGURATION.md    # V2 config settings
├── FEATURE_GLOSSARY.md # V2 terminology
├── V2_PROMPT_REQUIREMENTS.md # LLM prompt specs
└── v1/                 # Archived V1 docs
    ├── API.md
    ├── ARCHITECTURE.md
    ├── CLI_REFERENCE.md
    └── ...
```
