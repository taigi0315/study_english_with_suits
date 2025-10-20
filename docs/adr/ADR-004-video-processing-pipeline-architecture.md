# ADR-004: Video Processing Pipeline Architecture

**Date:** 2025-10-19  
**Status:** Accepted  
**Deciders:** Development Team  

## Context

LangFlix processes TV show content to create educational videos by extracting relevant clips, adding subtitles, and generating educational slides. The video processing workflow involves multiple steps:

1. **Video File Discovery**: Finding corresponding video files for subtitle files
2. **Clip Extraction**: Extracting specific time segments based on analyzed expressions
3. **Subtitle Overlay**: Adding dual-language subtitles to video clips
4. **Slide Generation**: Creating educational slides with expression information
5. **Final Assembly**: Combining context clips and slides into final educational videos

The original implementation mixed concerns and had several architectural issues:

1. **Tight Coupling**: Video processing logic was tightly coupled with expression analysis
2. **Resource Management**: No proper cleanup of temporary files
3. **Error Handling**: Inconsistent error handling across video operations
4. **Testability**: Difficult to test video processing components in isolation
5. **Scalability**: No clear separation of concerns made it hard to optimize or parallelize

## Decision

We will implement a modular pipeline architecture with clear separation of concerns for video processing operations.

### Architecture Design

The video processing pipeline follows a **Pipeline Pattern** with distinct stages and clear interfaces between components:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Video        │    │   Subtitle       │    │   Video        │
│  Processor     │───▶│   Processor      │───▶│   Editor       │
│                 │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
                                                         ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Output        │    │   Expression     │    │   Final        │
│  Manager       │◀───│   Analysis       │───▶│   Assembly      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Component Responsibilities

#### 1. VideoProcessor
- **Responsibility**: Video file discovery, validation, and basic clip extraction
- **Interface**: Clean API for finding and extracting video clips

```python
class VideoProcessor:
    def __init__(self, media_dir: str = "assets/media"):
        self.media_dir = Path(media_dir)
        self.supported_formats = {'.mp4', '.mkv', '.avi', '.mov', '.wmv'}
    
    def find_video_file(self, subtitle_file_path: str) -> Optional[Path]:
        """Find corresponding video file for subtitle file."""
        
    def extract_clip(self, video_path: Path, start_time: str, end_time: str, output_path: Path) -> bool:
        """Extract video clip between specified timestamps."""
        
    def get_video_info(self, video_path: Path) -> Dict[str, Any]:
        """Get video metadata and properties."""
```

#### 2. SubtitleProcessor
- **Responsibility**: Subtitle file parsing, timing analysis, and dual-language subtitle creation

```python
class SubtitleProcessor:
    def __init__(self, subtitle_file: str):
        self.subtitle_file = Path(subtitle_file)
    
    def find_expression_timing(self, expression_text: str, start_time: str, end_time: str) -> Dict[str, str]:
        """Find precise timing for expression within time range."""
        
    def create_dual_language_subtitle_file(self, expression: ExpressionAnalysis, output_path: str) -> bool:
        """Create dual-language subtitle file for expression."""
```

#### 3. VideoEditor
- **Responsibility**: Advanced video operations, subtitle overlay, and slide generation

```python
class VideoEditor:
    def __init__(self, output_dir: str, language_code: str = "ko"):
        self.output_dir = Path(output_dir)
        self.language_code = language_code
    
    def add_subtitles_to_context(self, video_path: str, expression: ExpressionAnalysis) -> str:
        """Add dual-language subtitles to context video."""
        
    def create_educational_slide(self, expression: ExpressionAnalysis) -> str:
        """Create educational slide with expression details."""
        
    def concatenate_sequence(self, video_paths: List[str], output_path: str) -> bool:
        """Concatenate multiple videos into final sequence."""
```

#### 4. OutputManager
- **Responsibility**: Organized output directory structure and file management

```python
class OutputManager:
    @staticmethod
    def create_output_structure(subtitle_file: str, language_code: str, output_dir: str) -> Dict[str, Path]:
        """Create organized directory structure for outputs."""
```

### Pipeline Integration

The main pipeline orchestrates these components in a clear sequence:

```python
class LangFlixPipeline:
    def __init__(self, subtitle_file: str, video_dir: str, output_dir: str, language_code: str):
        # Initialize all processors
        self.video_processor = VideoProcessor(str(video_dir))
        self.subtitle_processor = SubtitleProcessor(str(subtitle_file))
        self.video_editor = VideoEditor(str(self.paths['language']['final_videos']), language_code)
        
    def _process_expressions(self):
        """Process each expression through the video pipeline."""
        for i, expression in enumerate(self.expressions):
            try:
                # Stage 1: Find and extract video clip
                video_file = self.video_processor.find_video_file(str(self.subtitle_file))
                success = self.video_processor.extract_clip(
                    video_file, expression.context_start_time, 
                    expression.context_end_time, temp_clip_path
                )
                
                if success:
                    # Stage 2: Process subtitles and add to video
                    context_video = self.video_editor.add_subtitles_to_context(
                        str(temp_clip_path), expression
                    )
                    
                    # Stage 3: Generate educational slide
                    slide_video = self.video_editor.create_educational_slide(expression)
                    
                    # Stage 4: Prepare for final assembly
                    self.prepare_for_assembly(context_video, slide_video, expression)
                    
            except Exception as e:
                logger.error(f"Error processing expression {i+1}: {e}")
                continue
```

## Consequences

### Positive

1. **Separation of Concerns**: Each component has a single, well-defined responsibility
2. **Testability**: Components can be tested in isolation with clear interfaces
3. **Maintainability**: Changes to one component don't affect others
4. **Reusability**: Components can be reused in different contexts
5. **Error Isolation**: Failures in one stage don't cascade through the pipeline
6. **Resource Management**: Clear ownership of resources and proper cleanup

### Negative

1. **Increased Complexity**: More classes and interfaces to understand
2. **Code Organization**: More files and potential for over-abstraction
3. **Initial Development**: More upfront design work required

### Risks

1. **Over-engineering**: Pipeline might be too complex for current needs
   - **Mitigation**: Start simple, add complexity only when needed

2. **Performance Overhead**: Multiple object instantiations and method calls
   - **Mitigation**: Profile and optimize where necessary, overhead is minimal

3. **Interface Evolution**: Changes to component interfaces might break compatibility
   - **Mitigation**: Clear versioning and backwards compatibility considerations

## Alternatives Considered

1. **Monolithic Video Handler**: Single class handling all video operations
   - **Rejected**: Too tightly coupled, difficult to test and maintain

2. **Event-Driven Architecture**: Components communicate through events
   - **Rejected**: Over-engineered for current requirements, adds unnecessary complexity

3. **Microservices Architecture**: Separate services for different components
   - **Rejected**: Overkill for a desktop application, adds deployment complexity

4. **Functional Pipeline**: Chain of pure functions for processing
   - **Rejected**: Video processing has too much state and side effects

## Implementation Details

### Directory Structure
```
langflix/
├── video_processor.py    # Video discovery and basic operations
├── subtitle_processor.py # Subtitle file operations
├── video_editor.py       # Advanced video editing and effects
├── output_manager.py     # Output directory management
└── main.py              # Pipeline orchestration
```

### Error Handling Strategy
- **Component Level**: Each component handles its own errors gracefully
- **Pipeline Level**: Pipeline continues processing other expressions if one fails
- **Resource Cleanup**: Automatic cleanup of temporary files using context managers

### Resource Management
```python
import tempfile
from contextlib import contextmanager

@contextmanager
def temp_video_directory():
    """Context manager for temporary video files."""
    temp_dir = tempfile.mkdtemp(prefix="langflix_")
    try:
        yield Path(temp_dir)
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
```

This architecture provides a solid foundation for video processing that is maintainable, testable, and extensible while keeping complexity at an appropriate level for the application's needs.
