# LangFlix Development Diary

## 📅 2025-01-27

### 🎯 Project Initialization
- **Goal**: Create a tool to learn English expressions from TV show subtitles
- **Target Show**: Suits (Season 1)
- **Technology Stack**: Python, Google Gemini API, pysrt

### 🏗️ Phase 1: Core Logic and Content Generation

#### ✅ Completed Tasks

**1. Project Structure Setup**
- Created modular project structure with `langflix/` package
- Set up proper Python package with `__init__.py` files
- Organized assets and documentation directories

**2. Subtitle Parser Implementation**
- **File**: `langflix/subtitle_parser.py`
- **Functionality**: Parse SRT subtitle files into structured data
- **Features**:
  - Support for multiple SRT formats
  - Time format conversion (pysrt to custom format)
  - Chunking system for large files (4000 character limit)
  - Error handling for malformed files

**3. Expression Analyzer with Gemini API**
- **File**: `langflix/expression_analyzer.py`
- **Integration**: Google Gemini 2.5 Flash model
- **Features**:
  - Robust error handling for API failures
  - JSON response parsing with fallback
  - Logging system for debugging
  - Support for different model versions

**4. Advanced Prompt Engineering**
- **File**: `langflix/prompts.py`
- **Evolution**:
  - **v1**: Basic expression extraction
  - **v2**: Added context requirements and quality criteria
  - **v3**: Full dialogue inclusion with contextual translations
  - **v4**: Show context awareness ("Suits" TV show)
  - **v5**: Emphasized contextual vs literal translation

**5. Manual Testing Tools**
- **File**: `manual_prompt_test.py`
- **Purpose**: Allow manual prompt testing and optimization
- **Features**:
  - Chunk-by-chunk analysis
  - Prompt generation and display
  - Statistics (length, usage percentage)
  - Save prompts to files for manual testing

**6. Functional Testing**
- **File**: `test_suits_analysis.py`
- **Purpose**: End-to-end testing with real Suits subtitle data
- **Results**: Successfully analyzed 1,587 subtitle entries
- **Output**: Generated 2 valuable expressions with full context

### 🔧 Technical Improvements

**1. Error Handling**
- Comprehensive exception handling in all modules
- Graceful degradation for API failures
- Detailed logging for debugging

**2. Code Quality**
- Type hints throughout the codebase
- Comprehensive docstrings
- Modular design with clear separation of concerns

**3. Testing Infrastructure**
- **Unit Tests**: Individual component testing
- **Functional Tests**: End-to-end workflow testing
- **Integration Tests**: API interaction testing
- **Manual Tests**: Prompt optimization tools

### 📊 Current Status

**✅ Completed Features:**
- SRT subtitle parsing (1,587 entries processed)
- Gemini API integration (successful analysis)
- Advanced prompt engineering (5 iterations)
- Manual testing tools
- Complete project documentation

**🔄 In Progress:**
- Test organization and structure improvement
- Development diary maintenance

**📋 Next Phase (Phase 2):**
- Video processing and assembly
- Title card generation
- Final video creation with ffmpeg

### 🎯 Key Learnings

**1. Prompt Engineering**
- Context is crucial for meaningful translations
- Show-specific context improves model understanding
- Quality over quantity in expression selection
- Manual testing is essential for prompt optimization

**2. API Integration**
- Robust error handling is critical for production use
- Response parsing needs multiple fallback strategies
- Logging helps identify and resolve issues quickly

**3. Project Structure**
- Modular design enables easy testing and maintenance
- Clear separation between parsing, analysis, and testing
- Documentation is essential for project understanding

### 🚀 Achievements

1. **Successful API Integration**: Gemini API working with real data
2. **Advanced Prompting**: Context-aware, show-specific prompts
3. **Complete Testing Suite**: Unit, functional, and manual tests
4. **Production-Ready Code**: Error handling, logging, documentation
5. **GitHub Repository**: [https://github.com/taigi0315/study_english_with_suits.git](https://github.com/taigi0315/study_english_with_suits.git)

### 📈 Metrics

- **Subtitle Entries Processed**: 1,587
- **Chunks Created**: 13
- **Expressions Analyzed**: 2 (high-quality selection)
- **Test Coverage**: Unit, functional, integration, manual
- **Documentation**: Complete setup and usage guides

### 🔮 Future Plans

**Phase 2: Video Processing**
- Implement video clip extraction with ffmpeg
- Create title cards with expression and translation
- Assemble final educational videos

**Phase 3: Usability**
- CLI interface improvements
- Configuration management
- User-friendly error messages

---

## 📝 Development Notes

### Code Quality Standards
- All functions have type hints
- Comprehensive docstrings for all modules
- Error handling in all external API calls
- Logging for debugging and monitoring

### Testing Strategy
- Unit tests for individual components
- Functional tests for complete workflows
- Integration tests for API interactions
- Manual testing tools for prompt optimization

### Documentation Standards
- Clear setup instructions
- Comprehensive API documentation
- Development diary for progress tracking
- Code comments for complex logic
