# LangFlix - Learn English with Suits

🎬 **Learn English expressions from your favorite TV shows!**

LangFlix automatically analyzes TV show subtitles to extract valuable English expressions, idioms, and phrases, then creates educational content with contextual translations and definitions.

## 🚀 Features

- **Smart Subtitle Parsing**: Supports SRT subtitle files with automatic chunking
- **AI-Powered Analysis**: Uses Google Gemini API for intelligent expression extraction
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
│   ├── models.py            # Pydantic data models
│   └── settings.py          # Configuration settings
├── tests/                   # Test suite
│   ├── unit/               # Unit tests
│   ├── functional/         # End-to-end tests
│   ├── integration/        # API integration tests
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
```

## 📖 Usage

### 🚀 **Complete End-to-End Pipeline (Recommended)**

```bash
# Basic usage - process entire episode
python -m langflix.main --subtitle "assets/subtitles/Suits - season 1.en/Suits - 1x01 - Pilot.720p.WEB-DL.en.srt"

# Advanced options
python -m langflix.main \
  --subtitle "path/to/subtitle.srt" \
  --video-dir "assets/media" \
  --output-dir "output" \
  --dry-run

# Test mode (analysis only, no video processing)
python -m langflix.main --subtitle "path/to/subtitle.srt" --dry-run

# Language level specific analysis
python -m langflix.main --subtitle "path/to/subtitle.srt" --language-level beginner
python -m langflix.main --subtitle "path/to/subtitle.srt" --language-level intermediate
python -m langflix.main --subtitle "path/to/subtitle.srt" --language-level advanced

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

**Recent Achievements (October 17, 2025):**
- ✅ **End-to-End Pipeline**: Single command processes entire workflow
- ✅ **Language Level Support**: Beginner, Intermediate, Advanced, Mixed levels
- ✅ **LLM Output Review**: Save and analyze AI responses for debugging
- ✅ **LLM-Only Testing**: Test expression analysis without video processing
- ✅ **Real Content Testing**: Successfully processed Suits S01E01
- ✅ **Output Quality**: Generated high-quality learning videos with dual-language subtitles
- ✅ **Performance**: Optimized chunking and processing
- ✅ **Reliability**: Robust error handling and recovery mechanisms

### 📋 Phase 3: Production Readiness & Enhancement (Planned)
- [ ] Batch processing optimization
- [ ] User interface improvements
- [ ] Configuration management
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

- [Setup Guide](SETUP_GUIDE.md) - Detailed installation instructions
- [Development Diary](docs/development_diary.md) - Progress tracking
- [Project Plan](docs/project_plan.md) - High-level project overview
- [System Design](docs/system_design_and_development_plan.md) - Technical architecture

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
