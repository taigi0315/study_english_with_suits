# 파일명 Sanitization 유틸리티

**최종 업데이트:** 2025-01-30  
**위치:** `langflix/utils/filename_utils.py`

## 개요

`filename_utils` 모듈은 모든 플랫폼(Windows, macOS, Linux)에서 안전한 파일 시스템 작업을 위한 표준화된 파일명 sanitization 유틸리티를 제공합니다. 이 모듈은 이전에 여러 파일에 중복되어 있던 모든 파일명 sanitization 로직을 통합했습니다.

## 목적

- **보안**: 파일명 주입 공격 방지
- **크로스 플랫폼 호환성**: Windows, macOS, Linux에서 작동하는 파일명 보장
- **일관성**: 파일명 sanitization의 단일 소스
- **유지보수성**: 한 곳에서 sanitization 로직 업데이트

## 함수

### `sanitize_filename()`

텍스트를 안전한 파일명으로 sanitize하는 메인 함수입니다.

```python
from langflix.utils.filename_utils import sanitize_filename

# 기본 사용법
safe_name = sanitize_filename("Hello World!")
# 반환: "Hello_World"

# 확장자 보존
safe_name = sanitize_filename("test.file.mp4", allowed_extensions=['.mp4'])
# 반환: "testfile.mp4"

# 사용자 정의 최대 길이
safe_name = sanitize_filename("very long filename", max_length=50)
# 반환: 50자로 잘림
```

**매개변수:**
- `text` (str): sanitize할 입력 텍스트
- `max_length` (int, 선택): 출력의 최대 길이 (기본값: 100)
- `replace_spaces` (bool, 선택): True이면 공백을 밑줄로 대체 (기본값: True)
- `allowed_extensions` (list[str], 선택): 보존할 허용된 파일 확장자 목록

**반환:**
- `str`: Sanitize된 파일명 안전 문자열

**동작:**
- 모든 비-ASCII 영숫자 문자 제거
- 공백을 밑줄로 대체 (`replace_spaces=True`인 경우)
- 기본 이름에서 점 제거 (확장자의 점만 보존)
- 최대 길이 제한 적용
- 빈 입력이나 잘못된 입력의 경우 "untitled" 반환

### `sanitize_for_expression_filename()`

표현식 텍스트 sanitization을 위한 편의 래퍼입니다.

```python
from langflix.utils.filename_utils import sanitize_for_expression_filename

# 기본 사용법 (max_length=50)
safe_name = sanitize_for_expression_filename("How are you?")
# 반환: "How_are_you"

# 사용자 정의 최대 길이
safe_name = sanitize_for_expression_filename("long expression text", max_length=30)
# 반환: 30자로 잘림
```

**매개변수:**
- `expression` (str): sanitize할 표현식 텍스트
- `max_length` (int, 선택): 최대 길이 (기본값: 50)

**반환:**
- `str`: Sanitize된 파일명

### `sanitize_for_context_video_name()`

컨텍스트 비디오 파일명 sanitization을 위한 편의 래퍼입니다.

```python
from langflix.utils.filename_utils import sanitize_for_context_video_name

safe_name = sanitize_for_context_video_name("How are you?")
# 반환: "How_are_you" (max_length=50, 확장자 없음)
```

**매개변수:**
- `expression` (str): 표현식 텍스트

**반환:**
- `str`: Sanitize된 파일명 (확장자 없음)

## 상수

### `MAX_FILENAME_LENGTH`
표준 파일 시스템 제한: `255` 문자

### `DEFAULT_MAX_LENGTH`
대부분의 사용 사례에 합리적인 기본값: `100` 문자

## 사용 예제

### 기본 표현식 파일명

```python
from langflix.utils.filename_utils import sanitize_for_expression_filename

expression = "I'm gonna get screwed"
filename = sanitize_for_expression_filename(expression)
# filename = "Im_gonna_get_screwed"
```

### 컨텍스트 비디오 파일명

```python
from langflix.utils.filename_utils import sanitize_for_context_video_name

expression = "What's up?"
filename = sanitize_for_context_video_name(expression)
# filename = "Whats_up"
video_path = f"context_{filename}.mkv"
```

### 확장자 보존

```python
from langflix.utils.filename_utils import sanitize_filename

text = "my video file.mkv"
filename = sanitize_filename(text, allowed_extensions=['.mkv'])
# filename = "my_video_file.mkv"
```

### 사용자 정의 길이 제한

```python
from langflix.utils.filename_utils import sanitize_filename

long_text = "this is a very long expression that needs truncation"
filename = sanitize_filename(long_text, max_length=30)
# filename = "this_is_a_very_long_expres" (30자로 잘림)
```

## 크로스 플랫폼 호환성

Sanitization 함수는 플랫폼 간 호환성을 보장합니다:

- **Windows**: 예약된 문자 제거 (`<>:"/\|?*`)
- **macOS**: 대소문자 구분 없는 파일 시스템 문제 처리
- **Linux**: POSIX 파일명 표준 준수
- **ASCII 전용**: 최대 호환성을 위해 유니코드 문자 제거

## 문자 처리

**허용된 문자:**
- 문자 (a-z, A-Z)
- 숫자 (0-9)
- 밑줄 (_)
- 하이픈 (-)
- 점 (확장자에만)

**제거된 문자:**
- 특수 문자 (`@#$%^&*()[]{}` 등)
- 공백 (밑줄로 대체)
- 유니코드 문자 (제거)
- 예약된 파일 시스템 문자

## 마이그레이션 참고사항

이 유틸리티는 다음 중복 구현을 대체합니다:

- `langflix/main.py`의 `LangFlixPipeline._sanitize_filename()`
- `langflix/core/video_editor.py`의 `VideoEditor._sanitize_filename()`
- `langflix/subtitles/overlay.py`의 `sanitize_expression_for_filename()`
- `langflix/api/routes/jobs.py`의 다양한 인라인 sanitization 로직

모든 기존 코드가 이 유틸리티를 사용하도록 마이그레이션되어 코드베이스 전반에서 일관된 동작을 보장합니다.

## 테스트

`tests/unit/test_filename_utils.py`에 포괄적인 단위 테스트가 있으며, 다음을 다룹니다:
- 기본 sanitization
- 특수 문자 처리
- 길이 제한
- 확장자 보존
- 크로스 플랫폼 호환성
- 엣지 케이스 (빈 문자열, 유니코드 등)

## 관련 문서

- [TempFileManager](./temp_file_manager_kor.md) - 임시 파일 관리
- [Core Video Editor](../core/README_kor.md) - 비디오 편집 유틸리티
- [TICKET-004](../tickets/approved/TICKET-004-consolidate-filename-sanitization.md) - 통합 티켓

