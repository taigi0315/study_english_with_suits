# TempFileManager - 임시 파일 관리 유틸리티

## 개요

`TempFileManager`는 Python 컨텍스트 매니저를 사용하여 자동 정리 기능이 있는 중앙 집중식 임시 파일 관리를 제공합니다. 예외가 발생하더라도 임시 파일이 적절히 정리되어 디스크 공간 누수와 시스템 불안정을 방지합니다.

## 기능

- **자동 정리**: 컨텍스트가 종료되면 예외 발생 시에도 파일이 자동으로 삭제됩니다
- **크로스 플랫폼**: Python 표준 `tempfile` 모듈 사용으로 호환성 보장
- **전역 싱글톤**: 애플리케이션 전체에서 단일 인스턴스가 모든 임시 파일을 관리
- **수동 등록**: 외부에서 생성된 파일도 정리를 위해 등록 가능
- **디렉토리 지원**: 임시 디렉토리도 생성 및 관리 가능
- **종료 핸들러**: `atexit`를 통해 애플리케이션 종료 시 모든 파일 자동 정리

## 사용법

### 기본 파일 생성

```python
from langflix.utils.temp_file_manager import get_temp_manager

manager = get_temp_manager()

# 임시 파일 생성 (자동 정리됨)
with manager.create_temp_file(suffix='.mkv') as temp_path:
    # temp_path를 파일 작업에 사용
    temp_path.write_bytes(b"video content")
    # 컨텍스트 종료 시 파일이 자동으로 삭제됨
```

### 커스텀 Prefix 및 Suffix

```python
with manager.create_temp_file(suffix='.srt', prefix='subtitle_') as temp_path:
    temp_path.write_text("subtitle content")
```

### 파일 유지 (delete=False)

```python
# 컨텍스트 종료 후에도 유지되는 파일 생성
with manager.create_temp_file(suffix='.mkv', delete=False) as temp_path:
    temp_path.write_bytes(b"content")
    # 컨텍스트 종료 후에도 파일이 존재함
    output_path = temp_path  # 다른 곳에서 사용 가능

# 나중에 수동으로 정리를 위해 등록
manager.register_file(output_path)
# cleanup_all() 또는 종료 시 정리됨
```

### 임시 디렉토리

```python
with manager.create_temp_dir() as temp_dir:
    # 디렉토리 내에 파일 생성
    (temp_dir / "file1.txt").write_text("content1")
    (temp_dir / "file2.txt").write_text("content2")
    # 컨텍스트 종료 시 디렉토리와 모든 내용이 자동으로 삭제됨
```

### 수동 파일 등록

```python
# 외부에서 생성된 파일을 정리를 위해 등록
external_file = Path("/some/path/file.txt")
external_file.write_text("content")

manager.register_file(external_file)
# cleanup_all() 또는 종료 시 정리됨
```

### 모든 파일 정리

```python
# 등록된 모든 파일 수동 정리 트리거
manager.cleanup_all()
```

## API 레퍼런스

### `get_temp_manager() -> TempFileManager`

전역 싱글톤 TempFileManager 인스턴스를 가져옵니다.

**반환:** `TempFileManager` - 전역 인스턴스

### `TempFileManager.__init__(prefix: str = "langflix_", base_dir: Optional[Path] = None)`

임시 파일 매니저를 초기화합니다.

**매개변수:**
- `prefix` (str): 임시 파일 및 디렉토리의 접두사 (기본값: "langflix_")
- `base_dir` (Optional[Path]): 임시 파일의 기본 디렉토리 (기본값: 시스템 temp 디렉토리)

### `TempFileManager.create_temp_file(suffix: str = "", prefix: Optional[str] = None, delete: bool = True) -> Generator[Path, None, None]`

자동 정리 기능이 있는 임시 파일을 생성합니다.

**매개변수:**
- `suffix` (str): 파일 접미사 (예: '.mkv', '.srt')
- `prefix` (Optional[str]): 접두사 재정의 (선택사항)
- `delete` (bool): True인 경우 컨텍스트 종료 시 파일 삭제 (기본값: True)

**Yields:** `Path` - 임시 파일 경로

### `TempFileManager.create_temp_dir(prefix: Optional[str] = None) -> Generator[Path, None, None]`

자동 정리 기능이 있는 임시 디렉토리를 생성합니다.

**매개변수:**
- `prefix` (Optional[str]): 접두사 재정의 (선택사항)

**Yields:** `Path` - 임시 디렉토리 경로

### `TempFileManager.register_file(file_path: Path) -> None`

정리를 위해 파일을 수동으로 등록합니다.

**매개변수:**
- `file_path` (Path): 등록할 파일 경로

### `TempFileManager.cleanup_all() -> None`

등록된 모든 임시 파일 및 디렉토리를 정리합니다.

## 마이그레이션 가이드

### 이전 (하드코딩된 경로)

```python
import tempfile
import os

temp_video_path = f"/tmp/{job_id}_video.mkv"
with open(temp_video_path, 'wb') as f:
    f.write(video_content)

# ... 파일 사용 ...

# 수동 정리 (놓치기 쉬움)
try:
    os.unlink(temp_video_path)
except Exception as e:
    logger.warning(f"정리 오류: {e}")
```

### 이후 (TempFileManager)

```python
from langflix.utils.temp_file_manager import get_temp_manager

manager = get_temp_manager()

with manager.create_temp_file(suffix='.mkv', prefix=f'{job_id}_video_') as temp_video_path:
    temp_video_path.write_bytes(video_content)
    # ... 파일 사용 ...
    # 컨텍스트 종료 시 자동 정리됨
```

## 모범 사례

1. **항상 컨텍스트 매니저 사용**: 자동 정리를 위해 `with` 문 사용
2. **delete=False 절약**: 컨텍스트를 넘어서 파일이 유지되어야 할 때만 사용
3. **외부 파일 등록**: 매니저 외부에서 파일을 생성하는 경우 등록
4. **정리 후 파일 접근 금지**: 컨텍스트 종료 시 파일이 삭제됨
5. **중첩 컨텍스트 작동**: 여러 컨텍스트 매니저를 안전하게 중첩 가능

## 장점

- **디스크 누수 방지**: 자동 정리로 파일이 남지 않음
- **예외 안전성**: 예외 발생 시에도 파일이 정리됨
- **일관된 패턴**: 모든 코드가 임시 파일에 대해 동일한 접근 방식 사용
- **쉬운 마이그레이션**: 기존 임시 파일 코드를 간단히 교체 가능
- **전역 추적**: 단일 매니저가 모든 임시 파일을 추적

