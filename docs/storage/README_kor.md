# Storage 모듈 문서

## 개요

`langflix/storage/` 모듈은 스토리지 백엔드를 위한 추상화 계층을 제공하며, 로컬 파일시스템과 Google Cloud Storage를 지원합니다.

**최종 업데이트:** 2025-01-30

## 목적

이 모듈은 다음을 제공합니다:
- 파일 작업을 위한 통합 스토리지 인터페이스
- 여러 스토리지 백엔드 지원 (로컬, GCS)
- 백엔드 생성을 위한 팩토리 패턴
- API 및 CLI 모드용 스토리지 추상화

## 주요 구성 요소

### StorageBackend (추상 기본 클래스)

**위치:** `langflix/storage/base.py`

모든 스토리지 백엔드가 구현해야 하는 추상 인터페이스:

```python
class StorageBackend(ABC):
    def save_file(local_path, remote_path) -> str
    def load_file(remote_path, local_path) -> bool
    def delete_file(remote_path) -> bool
    def list_files(prefix) -> List[str]
    def file_exists(remote_path) -> bool
    def get_file_url(remote_path) -> str
```

### LocalStorage

**위치:** `langflix/storage/local.py`

로컬 파일시스템 스토리지 백엔드:
- 로컬 디렉토리를 스토리지로 사용
- CLI와의 하위 호환성 유지
- 파일 경로는 기본 디렉토리 기준 상대 경로

### GoogleCloudStorage

**위치:** `langflix/storage/gcs.py`

Google Cloud Storage 백엔드:
- GCS 버킷에 파일 업로드
- GCS에서 파일 다운로드
- 서비스 계정 인증 지원

### StorageFactory

**위치:** `langflix/storage/factory.py`

스토리지 백엔드 생성을 위한 팩토리 함수:

```python
def create_storage_backend() -> StorageBackend:
    """설정 기반 스토리지 백엔드 생성."""
    
def create_storage_backend_with_config(backend_type: str, **kwargs) -> StorageBackend:
    """명시적 설정으로 스토리지 백엔드 생성."""
```

## 사용 예시

### 스토리지 백엔드 생성

```python
from langflix.storage.factory import create_storage_backend

# 설정에서 구성 사용
storage = create_storage_backend()

# 또는 명시적 설정으로
from langflix.storage.local import LocalStorage
storage = LocalStorage(Path("output"))
```

### 파일 저장

```python
storage.save_file(
    local_path=Path("local/video.mp4"),
    remote_path="episodes/s01e01/video.mp4"
)
```

### 파일 로드

```python
storage.load_file(
    remote_path="episodes/s01e01/video.mp4",
    local_path=Path("download/video.mp4")
)
```

## 관련 모듈

- `langflix.config/`: 스토리지 설정
- `langflix.db/`: 데이터베이스의 파일 경로 참조

