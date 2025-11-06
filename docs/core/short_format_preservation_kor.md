# Short Format 비디오 Expression 보존 기능

**최종 업데이트:** 2025-01-30  
**관련 티켓:** TICKET-029

## 개요

Short format (세로형 9:16) 비디오 생성 시, LangFlix는 저작권 규정 준수를 위해 개별 expression 비디오를 보존합니다. 이 비디오들은 일반적으로 10-60초 길이로, <60초 컨텐츠를 요구하는 플랫폼에서 저작권 문제를 피하기에 적합합니다.

## 기능이 필요한 이유

일부 비디오 컨텐츠는 저작권 하에 있어, 저작권 문제를 피하기 위해 60초 미만의 비디오가 필요합니다. Short video 처리 중 생성되는 개별 expression 비디오들이 이미 이 용도에 완벽하지만, 이전에는 배치 생성 직후 즉시 삭제되었습니다.

## 작동 방식

### 자동 보존

Short format 비디오 생성 시:

1. **비디오 생성 중**: 시스템이 `temp_vstack_short_{expression}.mkv` 파일들(완성된 개별 expression 비디오)을 추적합니다
2. **배치 생성 후**: 이 파일들이 삭제되지 않고 자동으로 보존됩니다
3. **파일 구조**: 보존된 파일들이 `short_form_videos/expressions/` 디렉토리로 이동됩니다
4. **파일 명명**: 파일 이름이 `temp_vstack_short_{expression}.mkv`에서 `expression_{expression_name}.mkv`로 변경됩니다

### 디렉토리 구조

```
output/Series/Episode/translations/ko/
└── short_form_videos/
    ├── short-form_{episode}_{batch_number}.mkv  # 배치된 비디오 (~120초)
    └── expressions/                              # 개별 expression 비디오 (<60초)
        ├── expression_{expression_1}.mkv
        ├── expression_{expression_2}.mkv
        └── ...
```

### 파일 위치

- **배치 비디오**: `short_form_videos/short-form_{episode}_{batch_number}.mkv` - ~120초, 여러 expression 결합
- **개별 Expression 비디오**: `short_form_videos/expressions/expression_{expression_name}.mkv` - 10-60초, 단일 expression
- **최종 개별 비디오**: `context_slide_combined/short_{expression}.mkv` - 배치 전 생성된 파일도 사용 가능

## 사용 방법

### 보존된 비디오 접근

보존된 expression 비디오는 `expressions/` 하위 디렉토리에서 자동으로 사용 가능합니다:

```python
from pathlib import Path

# 보존된 expression 비디오 가져오기
short_videos_dir = Path("output/Series/Episode/translations/ko/short_form_videos")
expressions_dir = short_videos_dir / "expressions"

# 보존된 모든 expression 비디오 리스트
expression_videos = list(expressions_dir.glob("expression_*.mkv"))
```

### 비디오 길이

보존된 expression 비디오는 일반적으로:
- **최소**: ~10초 (컨텍스트 클립 + expression)
- **최대**: ~60초 (긴 컨텍스트 + expression 반복)
- **평균**: 15-30초

모든 보존된 비디오는 60초 미만으로, 저작권 규정 준수 업로드에 적합합니다.

## 기술적 세부사항

### 구현

- **추적**: `VideoEditor.short_format_temp_files` 리스트가 보존할 파일들을 추적합니다
- **보존**: `_preserve_short_format_files()` 메서드가 파일들을 영구 위치로 이동시킵니다
- **정리**: `preserve_short_format` 파라미터를 사용한 조건부 정리
- **Long Form**: Long form 비디오는 계속해서 모든 임시 파일을 삭제합니다 (기존 동작 유지)

### 정리 동작

- **Short Format 비디오**: `preserve_short_format=True`일 때 expression 비디오 보존
- **Long Form 비디오**: `preserve_short_format=False`일 때 모든 임시 파일 삭제 (기본값)
- **정리 타이밍**: 보존은 short video 배치 생성 후, long form 정리 전에 발생합니다

## 설정

설정 불필요 - short format 비디오에 대해 자동으로 보존됩니다.

## 파일 명명 규칙

- **원본**: `temp_vstack_short_{expression_name}.mkv`
- **보존**: `expression_{expression_name}.mkv`

명확성을 위해 "temp_" 접두사가 제거되고, "vstack_short_"는 완성된 개별 expression 비디오임을 나타내는 "expression_"으로 단순화됩니다.

## 관련 기능

- **TICKET-019**: Short video 길이 제한 (<60초)
- **TICKET-025**: Short video용 여러 expression per context
- **ADR-006**: Short video 아키텍처

## 문제 해결

### 파일이 보존되지 않음

Expression 비디오가 보존되지 않는 경우:

1. Short video 생성이 활성화되어 있는지 확인 (`short_video.enabled: true`)
2. `_create_short_videos()`가 호출되는지 확인
3. 로그에서 보존 메시지 확인: `✅ Preserved short format expression video`
4. `short_form_videos/expressions/` 디렉토리가 존재하는지 확인

### 디스크 공간

보존된 expression 비디오는 추가 디스크 공간을 사용합니다:
- 각 비디오: ~5-20 MB (길이에 따라 다름)
- 일반적인 에피소드: 10-20개 expression = ~50-400 MB 추가 공간
- 프로덕션 환경에서 디스크 사용량 모니터링 권장

## 예제

### 저작권 규정 준수 비디오 찾기

```python
from pathlib import Path

def find_short_videos_for_upload(episode_path: Path):
    """저작권 규정 준수 업로드를 위해 60초 미만의 모든 expression 비디오 찾기"""
    expressions_dir = episode_path / "short_form_videos" / "expressions"
    
    if not expressions_dir.exists():
        return []
    
    # expressions 디렉토리의 모든 비디오는 60초 미만입니다
    return list(expressions_dir.glob("expression_*.mkv"))
```

### 비디오 길이 확인

```python
from langflix.media.ffmpeg_utils import get_duration_seconds

def verify_copyright_compliance(video_path: Path) -> bool:
    """비디오가 저작권 규정 준수를 위해 60초 미만인지 확인"""
    duration = get_duration_seconds(str(video_path))
    return duration < 60.0
```

