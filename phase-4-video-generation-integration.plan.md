# Phase 4: Video Generation Integration

## Overview

Phase 4에서는 north-start-doc.md의 계획에 따라 Media Slicing & Processing을 구현합니다. WhisperX로부터 얻은 정확한 타임스탬프를 활용하여 표현식별 비디오 클립을 생성하고, 교육용 슬라이드를 생성하는 기능을 구현합니다.

## Implementation Plan

### 1. 준비 작업

**Git 작업**:
- 현재 브랜치: `phase-4-video-generation-integration` (이미 생성됨)
- Phase 3 완료 상태 확인

### 2. Media Slicing & Processing (4.1)

#### 2.1 Media File Validation

**새 파일**: `langflix/media/__init__.py`
```python
# Package initialization
```

**새 파일**: `langflix/media/media_validator.py`
```python
from dataclasses import dataclass
from typing import Tuple, Optional
import subprocess
import json
from pathlib import Path

@dataclass
class MediaMetadata:
    """Media file metadata"""
    path: str
    duration: float
    video_codec: str
    audio_codec: str
    resolution: Tuple[int, int]
    fps: float
    bitrate: int
    has_video: bool
    has_audio: bool

class MediaValidator:
    """Validate and extract media metadata"""
    
    def validate_media(self, media_path: str) -> MediaMetadata:
        """Validate and extract media metadata using FFprobe"""
        # FFprobe를 사용한 미디어 파일 검증
        # 메타데이터 추출 및 반환
```

**새 파일**: `langflix/media/exceptions.py`
```python
class MediaValidationError(Exception):
    """Raised when media validation fails"""
    pass

class VideoSlicingError(Exception):
    """Raised when video slicing fails"""
    pass

class SubtitleRenderingError(Exception):
    """Raised when subtitle rendering fails"""
    pass
```

#### 2.2 Expression Video Slicing

**새 파일**: `langflix/media/expression_slicer.py`
```python
from pathlib import Path
from typing import List
import subprocess
from langflix.asr.timestamp_aligner import AlignedExpression
from langflix.media.media_validator import MediaMetadata
from langflix.storage.base import StorageBackend
import logging

class ExpressionMediaSlicer:
    """Slice media files for expressions using FFmpeg"""
    
    def __init__(
        self,
        storage_backend: StorageBackend,
        output_dir: Path,
        quality: str = 'high'
    ):
        """Initialize with existing storage backend"""
    
    async def slice_expression(
        self,
        media_path: str,
        aligned_expression: AlignedExpression,
        media_id: str
    ) -> str:
        """Slice media file for expression"""
        # FFmpeg를 사용한 정확한 타임스탬프 기반 비디오 슬라이싱
        # 버퍼 시간 포함하여 클립 생성
        # 스토리지 백엔드에 업로드
```

#### 2.3 Subtitle Rendering

**새 파일**: `langflix/media/subtitle_renderer.py`
```python
from pathlib import Path
from typing import List, Dict, Any
import subprocess
from langflix.core.models import ExpressionAnalysis
from langflix import settings
import logging

class SubtitleRenderer:
    """Render subtitles for expression videos"""
    
    def __init__(self, output_dir: Path):
        """Initialize subtitle renderer"""
    
    def render_expression_subtitles(
        self,
        expression: ExpressionAnalysis,
        video_path: str,
        output_path: str
    ) -> str:
        """Render subtitles for expression video"""
        # 기존 설정에서 자막 스타일 가져오기
        # FFmpeg를 사용한 자막 렌더링
        # 하이라이트된 표현식 표시
```

### 3. Educational Slide Generation (4.2)

#### 3.1 Slide Content Generation

**새 파일**: `langflix/slides/__init__.py`
```python
# Package initialization
```

**새 파일**: `langflix/slides/slide_generator.py`
```python
from dataclasses import dataclass
from typing import List, Optional
from langflix.llm.gemini_client import GeminiClient
from langflix.core.models import ExpressionAnalysis
import logging

@dataclass
class SlideContent:
    """Educational slide content"""
    expression_text: str
    translation: str
    pronunciation: str
    difficulty_level: int
    category: str
    usage_examples: List[str]
    cultural_notes: Optional[str]
    grammar_notes: Optional[str]

class SlideContentGenerator:
    """Generate educational content for slides"""
    
    def __init__(self, gemini_client: GeminiClient):
        """Initialize with existing Gemini client"""
    
    async def generate_slide_content(
        self,
        expression: ExpressionAnalysis
    ) -> SlideContent:
        """Generate educational content for slide"""
        # Gemini API를 사용한 교육용 콘텐츠 생성
        # 발음, 사용 예시, 문화적 배경 등 포함
```

#### 3.2 Slide Templates

**새 파일**: `langflix/slides/slide_templates.py`
```python
from dataclasses import dataclass
from typing import Dict, Any
from enum import Enum

class SlideType(Enum):
    """Slide template types"""
    EXPRESSION = "expression"
    USAGE = "usage"
    CULTURAL = "cultural"
    GRAMMAR = "grammar"

@dataclass
class SlideTemplate:
    """Slide template configuration"""
    template_type: SlideType
    background_color: str
    text_color: str
    font_family: str
    font_size: int
    layout: Dict[str, Any]

class SlideTemplates:
    """Manage slide templates"""
    
    def __init__(self):
        """Initialize with default templates"""
    
    def get_template(self, slide_type: SlideType) -> SlideTemplate:
        """Get template for slide type"""
        # 템플릿별 설정 반환
```

#### 3.3 Slide Rendering

**새 파일**: `langflix/slides/slide_renderer.py`
```python
from pathlib import Path
from typing import Tuple
from PIL import Image, ImageDraw, ImageFont
from langflix.slides.slide_templates import SlideTemplate, SlideContent
import logging

class SlideRenderer:
    """Render educational slides"""
    
    def __init__(self, output_dir: Path):
        """Initialize slide renderer"""
    
    def render_slide(
        self,
        template: SlideTemplate,
        content: SlideContent,
        output_path: str,
        size: Tuple[int, int] = (1920, 1080)
    ) -> str:
        """Render slide with content"""
        # PIL을 사용한 슬라이드 렌더링
        # 템플릿과 콘텐츠를 결합하여 이미지 생성
```

### 4. Integration with Existing System

#### 4.1 Enhanced Video Processor

**수정 파일**: `langflix/core/video_processor.py`

기존 `VideoProcessor`에 다음 기능 추가:
- WhisperX 결과와의 통합
- Expression slicing 기능
- Subtitle rendering 통합

#### 4.2 Configuration Updates

**수정 파일**: `langflix/config/default.yaml`

```yaml
# Add media processing settings
media:
  slicing:
    quality: high  # low, medium, high, lossless
    buffer_start: 0.2  # seconds before expression
    buffer_end: 0.2    # seconds after expression
    output_format: mp4
  
  subtitles:
    style: expression_highlight
    font_size: 24
    font_color: "#FFFFFF"
    background_color: "#000000"
    highlight_color: "#FFD700"

# Add slide generation settings
slides:
  templates:
    expression:
      background_color: "#1a1a1a"
      text_color: "#ffffff"
      font_family: "DejaVu Sans"
      font_size: 48
    usage:
      background_color: "#2d2d2d"
      text_color: "#ffffff"
      font_family: "DejaVu Sans"
      font_size: 36
```

### 5. Testing

#### 5.1 Unit Tests

**새 파일**: `tests/unit/test_media_validator.py`
```python
def test_media_validation():
    """Test media file validation"""
    
def test_metadata_extraction():
    """Test metadata extraction from various formats"""
    
def test_error_handling():
    """Test error handling for invalid files"""
```

**새 파일**: `tests/unit/test_expression_slicer.py`
```python
def test_expression_slicing():
    """Test expression video slicing"""
    
def test_quality_settings():
    """Test different quality settings"""
    
def test_storage_integration():
    """Test storage backend integration"""
```

**새 파일**: `tests/unit/test_subtitle_renderer.py`
```python
def test_subtitle_rendering():
    """Test subtitle rendering"""
    
def test_style_application():
    """Test subtitle style application"""
```

**새 파일**: `tests/unit/test_slide_generator.py`
```python
def test_slide_content_generation():
    """Test slide content generation"""
    
def test_slide_rendering():
    """Test slide rendering"""
    
def test_template_system():
    """Test slide template system"""
```

#### 5.2 Integration Tests

**새 파일**: `tests/integration/test_media_processing.py`
```python
def test_complete_media_processing():
    """Test complete media processing pipeline"""
    
def test_expression_to_slide_workflow():
    """Test expression to slide workflow"""
    
def test_storage_backend_integration():
    """Test storage backend integration"""
```

### 6. Documentation

#### 6.1 ADR Documentation

**새 파일**: `docs/adr/ADR-016-media-slicing-processing.md`
```markdown
# ADR-016: Media Slicing & Processing Architecture

## Context
- WhisperX로부터 정확한 타임스탬프 획득
- 표현식별 비디오 클립 생성 필요
- 교육용 슬라이드 생성 필요

## Decision
- FFmpeg 기반 미디어 슬라이싱
- PIL 기반 슬라이드 렌더링
- 기존 스토리지 백엔드 활용

## Consequences
- 정확한 타임스탬프 기반 클립 생성
- 교육용 콘텐츠 자동 생성
- 확장 가능한 템플릿 시스템
```

#### 6.2 User Manual Updates

**수정 파일**: `docs/en/USER_MANUAL.md`, `docs/ko/USER_MANUAL_KOR.md`

- Media processing 설정 설명
- Slide generation 설정 설명
- Quality settings 가이드
- Template customization 가이드

## Implementation Order

1. Media validation & metadata extraction
2. Expression video slicing
3. Subtitle rendering
4. Slide content generation
5. Slide templates & rendering
6. Integration with existing system
7. Unit tests (media, slicing, subtitles, slides)
8. Integration tests
9. Documentation (ADR-016, User Manual)
10. End-to-end testing (S01E01, S01E02)

## Completion Criteria

- [ ] Media validation with FFprobe
- [ ] Expression video slicing with FFmpeg
- [ ] Subtitle rendering with styling
- [ ] Slide content generation with Gemini
- [ ] Slide templates and rendering
- [ ] Storage backend integration
- [ ] Unit tests coverage > 90%
- [ ] Integration tests passing
- [ ] Documentation complete (ADR-016, User Manual)
- [ ] S01E01/S01E02 tests successful

## Files to Create/Modify

### New Files:
- `langflix/media/__init__.py`
- `langflix/media/media_validator.py`
- `langflix/media/expression_slicer.py`
- `langflix/media/subtitle_renderer.py`
- `langflix/media/exceptions.py`
- `langflix/slides/__init__.py`
- `langflix/slides/slide_generator.py`
- `langflix/slides/slide_templates.py`
- `langflix/slides/slide_renderer.py`
- `tests/unit/test_media_validator.py`
- `tests/unit/test_expression_slicer.py`
- `tests/unit/test_subtitle_renderer.py`
- `tests/unit/test_slide_generator.py`
- `tests/integration/test_media_processing.py`
- `docs/adr/ADR-016-media-slicing-processing.md`

### Modified Files:
- `langflix/core/video_processor.py` (integration)
- `langflix/config/default.yaml` (new settings)
- `docs/en/USER_MANUAL.md` (documentation)
- `docs/ko/USER_MANUAL_KOR.md` (documentation)
