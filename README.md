# LangFlix - Learn English with Suits

🎬 **Learn English expressions from your favorite TV shows!**

LangFlix automatically analyzes TV show subtitles to extract valuable English expressions, idioms, and phrases, then creates educational content with contextual translations and definitions.

## 🎉 Phase 1 Complete!

**✅ API-based video processing is now fully operational!**

- 🚀 **FastAPI Service**: Complete REST API for video processing
- 🎯 **All CLI Features**: Every CLI feature now available via API endpoints
- 📱 **Background Processing**: Asynchronous video processing with job tracking
- 🔧 **Production Ready**: Tested with multiple episodes (S01E01-S01E04)
- 📊 **Job Management**: Real-time progress tracking and status monitoring

## 🚀 Features

- **Smart Subtitle Parsing**: Supports SRT subtitle files with automatic chunking
- **AI-Powered Analysis**: Uses Google Gemini API for intelligent expression extraction
- **Short Video Generation**: Creates 9:16 vertical videos with expression video playback and perfect audio-video sync
- **Natural TTS Audio**: High-quality text-to-speech using Gemini TTS with SSML control
- **Enhanced Educational Slides**: 5-section layout with full dialogue context
- **Language Level Support**: Beginner, Intermediate, Advanced, and Mixed levels
- **Video Processing**: Automatic video file mapping and precise clip extraction
- **Dual-Language Subtitles**: Generates synchronized subtitles with translations
- **Contextual Learning**: Provides full dialogue context and meaningful translations
- **Quality-Focused**: Selects only the most valuable expressions for learning
- **Frame-Accurate Processing**: 0.1-second precision in video clip extraction
- **LLM Output Review**: Save and review AI responses for analysis
- **Manual Testing Tools**: Optimize prompts and test different scenarios

## 📁 Project Structure

```
langflix/
├── langflix/                 # Main package
│   ├── subtitle_parser.py    # SRT file parsing
│   ├── expression_analyzer.py # Gemini API integration
│   ├── video_processor.py    # Video file processing & clip extraction
│   ├── subtitle_processor.py # Subtitle processing & translation
│   ├── prompts.py           # Advanced prompt engineering
│   ├── templates/           # External prompt templates
│   │   └── expression_analysis_prompt.txt
│   ├── models.py            # Pydantic data models
│   └── settings.py          # Configuration settings
├── tests/                   # Test suite
│   ├── unit/               # Unit tests
│   ├── functional/         # End-to-end tests
│   ├── integration/        # API integration tests
│   ├── step_by_step/       # Step-by-step workflow tests
│   └── test_output/        # Generated test files
├── assets/                  # Media assets
│   ├── subtitles/          # Suits Season 1 subtitles
│   └── media/              # Video files
├── docs/                   # Documentation
└── run_tests.py           # Test runner
```

## 🛠️ Installation

### Prerequisites
- Python 3.9+
- Google Gemini API key
- ffmpeg (for video processing)

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/taigi0315/study_english_with_suits.git
   cd study_english_with_suits
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env and add your GEMINI_API_KEY
   ```

5. **Prepare media files**

   LangFlix V2 supports two subtitle folder structures:

   **NEW (Netflix-style) Structure** (Recommended):
   ```bash
   assets/media/Suits/
   ├── Suits.S01E01.720p.HDTV.x264.mkv       # Video file
   ├── Suits.S01E02.720p.HDTV.x264.mkv
   └── Subs/                                  # Subtitles folder
       ├── Suits.S01E01.720p.HDTV.x264/       # Episode subtitle folder
       │   ├── 3_Korean.srt                   # Netflix indexed format
       │   ├── 6_English.srt
       │   ├── Spanish.srt                    # Translated (simple format)
       │   └── Korean.srt                     # Translated (simple format)
       └── Suits.S01E02.720p.HDTV.x264/
           └── ...
   ```

   **Legacy Structure** (Still Supported):
   ```bash
   assets/media/Suits/
   ├── Suits.S01E01.720p.HDTV.x264.mkv
   ├── Suits.S01E01.720p.HDTV.x264/           # Subtitle folder next to video
   │   ├── 3_Korean.srt
   │   └── 6_English.srt
   └── ...
   ```

   **Subtitle File Naming**:
   - **Netflix indexed format**: `{index}_{Language}.srt` (e.g., `3_Korean.srt`, `6_English.srt`)
   - **Simple format**: `{Language}.srt` (e.g., `Korean.srt`, `English.srt`)
   - Language names are case-insensitive (automatically normalized to Title Case)
   - Both formats are supported and auto-discovered

   **Automatic Subtitle Translation**:
   - Missing subtitle languages are automatically translated using Gemini 1.5 Pro
   - Translations use full episode context for better quality (no chunking)
   - Translated files are saved in simple format (`{Language}.srt`)
   ```

## ⚙️ Configuration

LangFlix uses YAML-based configuration files for easy customization. The system supports cascading configuration with environment variable overrides.

### Quick Setup

1. **Copy the example configuration**
   ```bash
   cp config/config.example.yaml config/config.yaml
   ```

2. **Edit `config.yaml`** to customize settings like:
   - Target language
   - Video quality settings  
   - Font sizes
   - LLM parameters
   - Expression limits (min/max per chunk)
   - Transition effects

### Configuration Structure

LangFlix loads configuration in this order (later overrides earlier):

1. **Default settings** (`langflix/config/default.yaml`) - Built-in defaults
2. **User configuration** (`config.yaml` at project root) - Your customizations  
3. **Environment variables** (e.g., `LANGFLIX_LLM_MAX_INPUT_LENGTH=5000`)

### Key Configuration Sections

**LLM Settings:**
```yaml
llm:
  max_input_length: 1680      # Characters per chunk (optimized for API)
  target_language: "Spanish"
  default_language_level: "intermediate"
  temperature: 0.1
  top_p: 0.8
  top_k: 40
  max_retries: 3              # API retry attempts
```

**Expression Limits:**
```yaml
processing:
  min_expressions_per_chunk: 1   # Minimum expressions per chunk
  max_expressions_per_chunk: 3   # Maximum expressions per chunk
```

**Video Processing:**
```yaml
video:
  codec: "libx264"
  preset: "fast"
  crf: 23
  resolution: "1920x1080"
```

**Font Settings:**
```yaml
font:
  sizes:
    expression: 48
    translation: 40
    default: 32
```

**Transitions:**
```yaml
transitions:
  enabled: true
  context_to_slide:
    type: "xfade"
    effect: "slideup"
    duration: 0.5
```

For complete configuration options, see `config.example.yaml` which includes all available settings with descriptions.

### Prompt Template Customization

LangFlix uses external prompt templates for easy customization. The main prompt template is located at:

```
langflix/templates/expression_analysis_prompt.txt
```

You can edit this file to:
- Modify expression selection criteria
- Adjust language level requirements
- Change output format instructions
- Update quality guidelines

The system automatically loads the template and applies your configuration variables (language level, expression limits, target language, etc.).

### Environment Variable Overrides

You can override any configuration value using environment variables with the format:
```bash
export LANGFLIX_LLM_MAX_INPUT_LENGTH=5000
export LANGFLIX_VIDEO_CRF=28
export LANGFLIX_TARGET_LANGUAGE="French"
```

## 🧪 Testing

### Run All Tests
```bash
python run_tests.py all
```

### Run Specific Test Types
```bash
# Unit tests only
python run_tests.py unit

# Functional tests (end-to-end)
python run_tests.py functional

# Integration tests (API)
python run_tests.py integration
```

### Step-by-Step Testing System 🧪

LangFlix includes a comprehensive step-by-step testing system that breaks down the entire workflow into 7 isolated test steps. This allows for detailed debugging and validation of each stage:

```bash
# Run individual steps for debugging
python tests/step_by_step/test_step1_load_and_analyze.py      # Load & analyze subtitles with LLM
python tests/step_by_step/test_step2_slice_video.py           # Extract context video clips  
python tests/step_by_step/test_step3_add_subtitles.py         # Add target language subtitles
python tests/step_by_step/test_step4_extract_audio.py         # Extract expression audio
python tests/step_by_step/test_step5_create_slide.py          # Create educational slides
python tests/step_by_step/test_step6_append_to_context.py     # Combine context + slides
python tests/step_by_step/test_step7_final_concat.py          # Create final video

# Run all steps in sequence
python tests/step_by_step/run_all_steps.py

# Clean all test outputs
python tests/step_by_step/cleanup_all.py
```

**Step-by-Step Workflow:**
1. **Step 1**: Load subtitles, chunk them, and analyze with Gemini API
2. **Step 2**: Extract video clips based on expression context timing  
3. **Step 3**: Add dual-language subtitles to context videos
4. **Step 4**: Extract precise audio for each expression phrase
5. **Step 5**: Create educational slides with background and text overlays
6. **Step 6**: Combine context videos with educational slides (includes transition effects)
7. **Step 7**: Concatenate all expressions into final educational video

Each step validates its output and provides detailed error reporting, making it easy to identify and fix issues at any stage of the pipeline.

### Manual Testing
```bash
# Test video clip extraction
python tests/functional/test_video_clip_extraction.py

# Test subtitle processing
python tests/functional/test_subtitle_processing.py

# Test prompt generation
python tests/functional/manual_prompt_test.py

# Test with specific chunk
python tests/functional/manual_prompt_test.py 2

# Full analysis test
python tests/functional/test_suits_analysis.py

# LLM-only test (no video processing)
python tests/functional/test_llm_only.py --subtitle "assets/subtitles/Suits.S01E01.720p.HDTV.x264.srt" --language-level beginner

# Complete End-to-End Test (NEW - Recommended)
python tests/functional/run_end_to_end_test.py
```

## 📦 Deployment Bundle

Need to copy the project to a deployment host (e.g., TrueNAS) without development artifacts?

```bash
# Create a minimal bundle under dist/
make deploy-zip

# Custom output filename
make deploy-zip OUTPUT=/tmp/langflix_deploy.zip

# Include documentation directory if desired
make deploy-zip INCLUDE_DOCS=1

# Include assets/media directory (opt-in)
make deploy-zip INCLUDE_MEDIA=1
```

The bundle contains the LangFlix application code, Docker/Compose resources, configuration templates, and assets required for deployment while omitting virtual environments, tests, caches, and other development-only files. Large media libraries under `assets/media` are excluded by default to keep the archive lean; opt in with `INCLUDE_MEDIA=1` when they are required.

## 📖 Usage

### 🚀 **Complete End-to-End Pipeline (Recommended)**

```bash
# Basic usage - process entire episode (new structure)
python -m langflix.main --subtitle "assets/media/Suits/Suits.S01E01.720p.HDTV.x264.srt" --video-dir "assets/media"

# Alternative - using subtitles folder
python -m langflix.main --subtitle "assets/subtitles/Suits - season 1.en/Suits - 1x01 - Pilot.720p.WEB-DL.en.srt"

# Advanced options
python -m langflix.main \
  --subtitle "path/to/subtitle.srt" \
  --video-dir "assets/media" \
  --output-dir "output" \
  --dry-run

# Test mode (analysis only, no video processing)
python -m langflix.main --subtitle "path/to/subtitle.srt" --dry-run

# Language level specific analysis (processes ALL found expressions by default)
python -m langflix.main --subtitle "path/to/subtitle.srt" --language-level beginner
python -m langflix.main --subtitle "path/to/subtitle.srt" --language-level intermediate
python -m langflix.main --subtitle "path/to/subtitle.srt" --language-level advanced

# Limit number of expressions (optional)
python -m langflix.main --subtitle "path/to/subtitle.srt" --max-expressions 5

# Save LLM output for review
python -m langflix.main --subtitle "path/to/subtitle.srt" --save-llm-output
```

### 🔧 **Individual Component Usage**

#### Basic Analysis
```python
from langflix.subtitle_parser import parse_srt_file
from langflix.expression_analyzer import analyze_chunk

# Parse subtitle file
subtitles = parse_srt_file("path/to/subtitle.srt")

# Analyze expressions (requires GEMINI_API_KEY)
results = analyze_chunk(subtitles[:10])  # First 10 entries
```

#### Video Processing
```python
from langflix.video_processor import VideoProcessor
from langflix.subtitle_processor import SubtitleProcessor

# Initialize processors
video_processor = VideoProcessor("assets/media")
subtitle_processor = SubtitleProcessor("path/to/subtitle.srt")

# Extract video clip
video_processor.extract_clip(
    video_path, 
    start_time="00:01:25,657", 
    end_time="00:01:32,230", 
    output_path="output_clip.mkv"
)

# Create dual-language subtitles
subtitle_processor.create_dual_language_subtitle_file(
    expression, 
    "output_subtitles.srt"
)
```

### Manual Prompt Testing
```bash
# Generate and test prompts
python tests/functional/manual_prompt_test.py

# Test specific chunk
python tests/functional/manual_prompt_test.py 2
```

## 🎯 Current Status

### ✅ Phase 1: Core Logic (Completed)
- [x] Subtitle parsing with pysrt
- [x] Gemini API integration
- [x] Advanced prompt engineering
- [x] Language level support (Beginner, Intermediate, Advanced, Mixed)
- [x] LLM output review and debugging
- [x] Manual testing tools
- [x] Complete test suite

### ✅ Phase 2: Video Processing (Completed)
- [x] Video file mapping and validation
- [x] Frame-accurate video clip extraction (0.1s precision)
- [x] Dual-language subtitle generation
- [x] Complete pipeline testing
- [x] Production-ready video processing
- [x] **End-to-end pipeline integration**
- [x] **Automated workflow orchestration**
- [x] **Command-line interface**

### 🎉 **CORE PIPELINE COMPLETE - READY FOR PRODUCTION USE**

**Recent Achievements (October 2025):**
- ✅ **Short Video Generation**: 9:16 vertical videos with expression video playback (no freeze frames)
- ✅ **Audio-Video Synchronization**: Perfect sync with expression video looping during audio repetition
- ✅ **Gemini TTS Integration**: Natural-sounding speech with SSML control
- ✅ **Enhanced Educational Slides**: 5-section layout with full dialogue context
- ✅ **Smart Subtitle Matching**: Handles truncated filenames automatically
- ✅ **Configuration Refactoring**: Cleaner, more maintainable code
- ✅ **Comprehensive Documentation**: Updated guides and API references
- ✅ **End-to-End Pipeline**: Single command processes entire workflow
- ✅ **Language Level Support**: Beginner, Intermediate, Advanced, Mixed levels
- ✅ **LLM Output Review**: Save and analyze AI responses for debugging
- ✅ **LLM-Only Testing**: Test expression analysis without video processing
- ✅ **Real Content Testing**: Successfully processed Suits S01E01

**V2 Updates (December 2025):**
- ✅ **Gemini 1.5 Pro Integration**: Full episode context for subtitle translation (2M token context window)
- ✅ **Non-Split Mode**: Process entire subtitle files without chunking for better quality
- ✅ **Automatic Subtitle Translation**: Missing languages translated automatically using full context
- ✅ **Netflix-Style Folder Structure**: New Subs/ folder structure with backward compatibility
- ✅ **Flexible File Naming**: Support both indexed (`3_Korean.srt`) and simple (`Korean.srt`) formats
- ✅ **Case-Insensitive Language Names**: Automatic normalization to Title Case
- ✅ **Robust Language Discovery**: Auto-discovers all available subtitle languages and variants
- ✅ **Dual-Language Workflow**: V2 mode uses both source and target subtitles for content selection
- ✅ **Output Quality**: Generated high-quality learning videos with dual-language subtitles
- ✅ **Performance**: Optimized chunking and processing
- ✅ **Reliability**: Robust error handling and recovery mechanisms

**Latest Infrastructure Enhancements:**
- ✅ **YAML Configuration Management**: External YAML-based settings with cascading configs and environment overrides
- ✅ **Cross-Platform Compatibility**: Enhanced font and path handling
- ✅ **API Reliability**: Circuit breaker pattern and intelligent retry logic
- ✅ **Memory Optimization**: Automatic resource cleanup and management
- ✅ **Expression Timing**: Advanced matching algorithms for precision
- ✅ **Input Validation**: Comprehensive security and error prevention
- ✅ **Production Logging**: Structured logging for monitoring and debugging
- ✅ **Test Coverage**: Comprehensive edge case testing for robustness
- ✅ **Step-by-Step Testing System**: 7-stage isolated testing for debugging and validation

### 📋 Phase 3: Production Readiness & Enhancement (Planned)
- [ ] Batch processing optimization
- [ ] User interface improvements
- [ ] Performance monitoring
- [ ] Advanced error recovery

## 📊 Example Output

```json
{
  "dialogues": [
    "I'm paying you millions,",
    "and you're telling me I'm gonna get screwed?"
  ],
  "translation": [
    "나는 당신에게 수백만 달러를 지불하고 있는데,",
    "당신은 내가 속임을 당할 것이라고 말하고 있나요?"
  ],
  "expression": "I'm gonna get screwed",
  "expression_translation": "속임을 당할 것 같아요",
  "context_start_time": "00:01:25,657",
  "context_end_time": "00:01:32,230",
  "similar_expressions": [
    "I'm going to be cheated",
    "I'm getting the short end of the stick"
  ]
}
```

## 🔧 Development

### Running Tests
```bash
# All tests
python run_tests.py all

# With coverage
python run_tests.py all --coverage
```

### Code Quality
- Type hints throughout
- Comprehensive docstrings
- Modular design
- Error handling and logging

## 📚 Documentation

### User Guides
- [User Manual](docs/en/USER_MANUAL.md) - Complete usage guide (English)
- [User Manual 한국어](docs/ko/USER_MANUAL_KOR.md) - 완전한 사용 가이드 (한국어)
- [Troubleshooting Guide](docs/en/TROUBLESHOOTING.md) - Common issues and solutions (English)
- [Troubleshooting Guide 한국어](docs/ko/TROUBLESHOOTING_KOR.md) - 일반적인 문제와 해결책 (한국어)
- [Setup Guide](SETUP_GUIDE.md) - Detailed installation instructions

### Technical Documentation
- [API Reference](docs/en/API_REFERENCE.md) - Programmatic usage guide (English)
- [API Reference 한국어](docs/ko/API_REFERENCE_KOR.md) - 프로그래밍 사용 가이드 (한국어)
- [Development Diary](docs/development_diary.md) - Progress tracking
- [System Design](docs/system_design_and_development_plan.md) - Technical architecture

### Advanced Topics
- [Deployment Guide](docs/en/DEPLOYMENT.md) - Production setup (English)
- [Deployment Guide 한국어](docs/ko/DEPLOYMENT_KOR.md) - 프로덕션 설정 (한국어)
- [Performance Guide](docs/en/PERFORMANCE.md) - Optimization tips (English)
- [Performance Guide 한국어](docs/ko/PERFORMANCE_KOR.md) - 최적화 팁 (한국어)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🙏 Acknowledgments

- **Suits TV Show**: For providing rich dialogue content
- **Google Gemini API**: For powerful language understanding
- **pysrt**: For robust subtitle file parsing
- **Python Community**: For excellent libraries and tools

---

**Happy Learning! 🎓**
