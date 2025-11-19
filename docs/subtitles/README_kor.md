# 자막 모듈

## 개요

`langflix/subtitles/` 모듈은 비디오 처리에 필요한 자막 오버레이 기능을 제공합니다. 자막 파일 위치 찾기, 컨텍스트 비디오 클립을 위한 타임스탬프 조정, FFmpeg 필터를 사용한 이중 언어 자막 적용을 처리합니다.

**목적:**
- 표현식에 대한 자막 파일 찾기 및 관리
- 소스 비디오에서 컨텍스트 클립을 추출할 때 자막 타임스탬프 조정
- 적절한 스타일링(ASS 형식의 force_style)으로 비디오에 자막 적용
- 이중 언어 자막 오버레이 지원

**사용 시기:**
- 표현식을 처리하고 컨텍스트 비디오에 자막을 오버레이해야 할 때
- 컨텍스트 클립을 추출하고 자막 타임스탬프를 조정해야 할 때
- 교육용 비디오에 스타일이 적용된 자막을 적용할 때

## 파일 목록

### `overlay.py`
자막 오버레이 작업을 위한 주요 모듈입니다.

**주요 함수:**
- `find_subtitle_file()` - 표현식에 대한 자막 파일 찾기
- `adjust_subtitle_timestamps()` - 컨텍스트 클립 추출 시 타임스탬프 조정
- `apply_subtitles_with_file()` - FFmpeg 자막 필터를 사용하여 비디오에 자막 적용
- `apply_dual_subtitle_layers()` - 컨텍스트 비디오 세그먼트에 원본 자막 적용
- `build_ass_force_style()` - 설정에서 ASS 형식 스타일 문자열 생성
- `drawtext_fallback_single_line()` - drawtext 필터를 사용한 폴백 방법

## 주요 구성 요소

### 자막 파일 위치 찾기

```python
def find_subtitle_file(subtitle_dir: Path, expression_text: str) -> Optional[Path]:
    """
    여러 패턴 매칭 전략을 사용하여 표현식에 대한 자막 파일을 찾습니다.
    
    시도되는 패턴:
    1. expression_*_{safe_expr[:30]}.srt
    2. expression_{safe_expr[:30]}.srt
    3. expression_*_{sanitized}.srt
    4. expression_{sanitized}.srt
    5. 부분 일치 폴백
    
    Returns:
        자막 파일이 발견되면 Path, 그렇지 않으면 None
    """
```

### 타임스탬프 조정

소스 비디오에서 컨텍스트 클립을 추출할 때, 자막은 원본 비디오의 절대 타임스탬프를 가지고 있습니다. `adjust_subtitle_timestamps()` 함수는 컨텍스트 시작 시간을 빼서 잘린 비디오와 자막을 정렬합니다.

### 자막 적용

모듈은 자막을 적용하는 두 가지 방법을 제공합니다:

1. **FFmpeg 자막 필터 사용 (권장)**
2. **drawtext 필터 사용 (폴백)**

### 이중 자막 레이어

`apply_dual_subtitle_layers()` 함수는 소스 비디오에서 컨텍스트 세그먼트를 추출하고 원본 자막을 적용합니다. 참고: 사용자 요구사항에 따라 청록색 표현식 자막 레이어는 제거되었습니다.

## 구현 세부사항

### ASS 스타일링

모듈은 설정에서 ASS (Advanced SubStation Alpha) 형식 스타일 문자열을 생성합니다.

### 타임스탬프 변환

SRT 타임스탬프 형식을 위한 내부 헬퍼 함수들이 제공됩니다.

## 의존성

**외부 라이브러리:**
- `ffmpeg-python` - 비디오 처리 및 자막 오버레이
- `pathlib` - 경로 조작

**내부 의존성:**
- `langflix.settings` - 설정 접근
- `langflix.utils.filename_utils` - 파일명 정리

## 일반적인 작업

### 컨텍스트 비디오에 자막 오버레이 추가

```python
from langflix.subtitles.overlay import apply_dual_subtitle_layers

output_video = apply_dual_subtitle_layers(
    video_path="source_video.mkv",
    original_subtitle_path="dual_lang.srt",
    expression_subtitle_path="",  # 사용되지 않음
    output_path="context_with_subtitles.mkv",
    context_start_seconds=120.5,
    context_end_seconds=150.0
)
```

## 주의사항 및 참고사항

### 중요 고려사항

1. **타임스탬프 조정:**
   - 컨텍스트 클립을 추출할 때 항상 타임스탬프를 조정하세요
   - 음수 시작 시간을 가진 자막은 0으로 클램핑됩니다
   - 컨텍스트 시작 전의 자막은 필터링됩니다

2. **자막 필터 성능:**
   - 전체 길이 비디오에서 `subtitles` 필터 사용은 느립니다
   - 항상 컨텍스트 세그먼트를 먼저 추출한 다음 자막을 적용하세요
   - 올바른 패턴은 `apply_dual_subtitle_layers()` 참조

3. **표현식 자막 레이어:**
   - 청록색 표현식 자막 레이어는 제거되었습니다
   - 원본 이중 언어 자막만 적용됩니다
   - `expression_subtitle_path` 매개변수는 API 호환성을 위해 유지되지만 사용되지 않습니다

## 관련 문서

- [Core Module](../core/README_eng.md) - 표현식 처리 및 비디오 편집
- [Media Module](../media/README_eng.md) - FFmpeg 유틸리티
- [Config Module](../config/README_eng.md) - 폰트 및 스타일링 설정

