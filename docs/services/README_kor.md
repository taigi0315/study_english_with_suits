# Services 모듈 문서

## 개요

`langflix/services/` 모듈은 API와 CLI 구현 간에 이전에 중복되었던 코드를 통합하여 비즈니스 로직에 대한 통합 인터페이스를 제공하는 서비스 레이어 클래스를 포함합니다.

**최종 업데이트:** 2025-11-02  
**관련 티켓:** TICKET-001-extract-pipeline-logic, TICKET-014-batch-video-processing-queue

## 목적

이 모듈은 다음을 제공합니다:
- API와 CLI 모두에서 사용할 수 있는 **통합 인터페이스**
- 중복을 제거하는 **코드 통합**
- 장기 실행 작업을 위한 **진행 상황 추적**
- 다른 진입점에서 **표준화된 결과 형식**

## 주요 구성 요소

### VideoPipelineService

API 엔드포인트와 CLI 명령 모두에서 사용하기 위해 `LangFlixPipeline`을 래핑하는 통합 비디오 처리 파이프라인 서비스입니다.

**위치:** `langflix/services/video_pipeline_service.py`

**목적:**
- API와 CLI 간 450줄 이상의 중복 코드 제거
- 비디오 처리 로직에 대한 단일 진실 공급원 제공
- API 작업 업데이트를 위한 진행 상황 추적 활성화

#### 주요 기능

**1. 통합 인터페이스**
```python
from langflix.services.video_pipeline_service import VideoPipelineService

service = VideoPipelineService(language_code="ko", output_dir="output")
result = service.process_video(
    video_path="path/to/video.mkv",
    subtitle_path="path/to/subtitle.srt",
    show_name="Suits",
    episode_name="S01E01",
    max_expressions=10,
    language_level="intermediate",
    progress_callback=my_callback
)
```

**2. 진행 상황 콜백 지원**
- 선택적 `progress_callback` 파라미터: `(progress: int, message: str) -> None`
- 진행 상황 마일스톤 자동 보고:
  - 10%: 초기화 중
  - 20%: 파이프라인 실행 중
  - 90%: 결과 수집 중
  - 100%: 완료

**3. 표준화된 결과 형식**
```python
{
    "expressions": List[dict],           # 처리된 표현식
    "educational_videos": List[str],     # 교육용 비디오 경로
    "short_videos": List[str],           # 짧은 형식 비디오 경로
    "final_video": str,                  # 최종 연결된 비디오 경로
    "output_directory": str,             # 출력 디렉토리 경로
    "summary": dict                      # 파이프라인 요약
}
```

#### API에서 사용

```python
# langflix/api/routes/jobs.py에서
from langflix.services.video_pipeline_service import VideoPipelineService

async def process_video_task(job_id: str, ...):
    service = VideoPipelineService(
        language_code=language_code,
        output_dir=output_dir
    )
    
    # 진행 상황 콜백이 Redis 업데이트
    def update_progress(progress: int, message: str):
        redis_manager.update_job(job_id, {
            "progress": progress,
            "current_step": message
        })
    
    result = service.process_video(
        video_path=temp_video_path,
        subtitle_path=temp_subtitle_path,
        show_name=show_name,
        episode_name=episode_name,
        progress_callback=update_progress,
        ...
    )
```

#### CLI에서 사용

```python
# CLI도 일관성을 위해 서비스를 사용할 수 있음
from langflix.services.video_pipeline_service import VideoPipelineService

service = VideoPipelineService(language_code="ko")
result = service.process_video(...)

# 또는 LangFlixPipeline을 직접 계속 사용 (둘 다 작동)
```

### BatchQueueService

Redis 기반 FIFO 큐 시스템을 사용하여 순차 작업 실행을 관리하는 배치 비디오 처리 서비스입니다.

**위치:** `langflix/services/batch_queue_service.py`

**목적:**
- 여러 비디오 처리 작업을 배치로 생성
- 순차 처리를 위해 작업을 큐에 추가
- 배치 및 개별 작업 상태 추적
- 작업 상태에서 배치 상태 계산

#### 주요 기능

**1. 배치 생성**
```python
from langflix.services.batch_queue_service import BatchQueueService

service = BatchQueueService()
result = service.create_batch(
    videos=[
        {
            'video_path': '/path/to/video1.mp4',
            'subtitle_path': '/path/to/subtitle1.srt',
            'episode_name': 'Episode 1',
            'show_name': 'Suits'
        },
        # ... 더 많은 비디오
    ],
    config={
        'language_code': 'ko',
        'language_level': 'intermediate',
        'max_expressions': 50,
        'test_mode': False,
        'no_shorts': False,
        'output_dir': 'output'
    }
)
# 반환: {'batch_id': 'uuid', 'total_jobs': 2, 'jobs': [...], 'status': 'PENDING'}
```

**2. 배치 상태 추적**
```python
batch_status = service.get_batch_status(batch_id)
# 다음 정보를 포함한 배치 정보 반환:
# - 전체 상태 (PENDING, PROCESSING, COMPLETED, FAILED, PARTIALLY_FAILED)
# - 개별 작업 상태
# - 진행 메트릭 (completed_jobs, failed_jobs, total_jobs)
```

**3. 상태 계산**
- `PENDING`: 모든 작업이 QUEUED 상태 (아직 시작되지 않음)
- `PROCESSING`: 최소 하나의 작업이 QUEUED 또는 PROCESSING 상태
- `COMPLETED`: 모든 작업이 성공적으로 완료됨
- `FAILED`: 모든 작업이 실패함
- `PARTIALLY_FAILED`: 완료된 작업과 실패한 작업이 혼합됨

**4. 배치 크기 제한**
- 최대 배치 크기: 배치당 50개 비디오 (`MAX_BATCH_SIZE`로 설정 가능)
- 검증을 통해 배치 크기가 제한을 초과하지 않도록 함

#### API에서 사용

```python
# langflix/api/routes/batch.py에서
from langflix.services.batch_queue_service import BatchQueueService

@router.post("/batch")
async def create_batch(request: BatchCreateRequest):
    service = BatchQueueService()
    
    # 배치 크기 검증
    if len(request.videos) > service.MAX_BATCH_SIZE:
        raise HTTPException(status_code=400, detail="배치 크기 초과")
    
    result = service.create_batch(
        videos=[video.dict() for video in request.videos],
        config=request.dict(exclude={'videos'})
    )
    return result
```

### QueueProcessor

FastAPI lifespan과 통합된 백그라운드 워커 패턴을 사용하여 Redis 큐에서 작업을 순차적으로 처리합니다.

**위치:** `langflix/services/queue_processor.py`

**목적:**
- 큐의 작업을 순차적으로 처리 (FIFO)
- 하나의 프로세서 인스턴스만 실행되도록 보장 (Redis lock)
- 시작 시 멈춘 작업 처리
- 작업 재큐잉을 통한 우아한 종료

#### 주요 기능

**1. 백그라운드 처리**
- FastAPI lifespan에서 비동기 백그라운드 작업으로 실행
- API 시작 시 자동 시작
- API 종료 시 우아하게 중지

**2. 프로세서 Lock**
- 단일 인스턴스 보장을 위해 Redis lock (`jobs:processor_lock`) 사용
- 30분마다 lock 갱신
- 중복 처리 방지

**3. 멈춘 작업 복구**
- 시작 시 PROCESSING 상태에서 1시간 이상 멈춘 작업 식별
- 멈춘 작업을 자동으로 FAILED로 표시
- 오래된 processing 마커 정리

**4. 비동기 처리**
- blocking `process_video()` 호출을 `run_in_executor()`로 실행
- 이벤트 루프 블로킹 방지
- 처리 중에도 동시 API 요청 허용

**5. 진행 상황 업데이트**
- 처리 중 Redis 작업 상태 업데이트
- 추적을 위해 `updated_at` 타임스탬프 포함
- 진행 상황 업데이트 실패해도 처리 계속 진행

**6. 에러 처리**
- 처리 에러 시 작업을 FAILED로 표시
- 작업이 배치의 일부인 경우 배치 상태 업데이트
- 완료/실패 시 processing 마커 제거

#### 통합

```python
# langflix/api/main.py에서
from langflix.services.queue_processor import QueueProcessor

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작
    queue_processor = QueueProcessor()
    queue_processor_task = asyncio.create_task(queue_processor.start())
    
    yield
    
    # 종료
    await queue_processor.stop()
    queue_processor_task.cancel()
```

#### 처리 흐름

1. **작업 큐잉**: 작업이 Redis 리스트 `jobs:queue`에 추가됨
2. **작업 클레임**: 프로세서가 원자적으로 작업을 PROCESSING으로 표시
3. **작업 처리**: 비디오 처리가 thread executor에서 실행됨
4. **진행 상황 업데이트**: 진행 상황 콜백이 Redis 작업 상태 업데이트
5. **작업 완료**: 작업이 COMPLETED/FAILED로 표시됨, 배치 상태 업데이트
6. **다음 작업**: 프로세서가 큐에서 다음 작업 선택

### PipelineRunner (레거시)

**위치:** `langflix/services/pipeline_runner.py`

**상태:** 여전히 사용 중 (`langflix/youtube/web_ui.py`에서 사용), 향후 `VideoPipelineService`로 마이그레이션 고려.

**참고:** 이전에 버그가 있었음 (정의되지 않은 `selected_expressions` 변수)이 TICKET-001에서 수정됨.

## 아키텍처 패턴

### 서비스 레이어 패턴

이 모듈은 서비스 레이어 패턴을 구현합니다:

```
┌─────────────┐         ┌──────────────┐         ┌──────────────────┐
│   API       │────────▶│   Service    │────────▶│   Core Logic     │
│  (routes)   │         │   (services) │         │   (main.py)      │
└─────────────┘         └──────────────┘         └──────────────────┘
        │                        │                        │
        │                        │                        │
        ▼                        ▼                        ▼
┌─────────────┐         ┌──────────────┐         ┌──────────────────┐
│   CLI       │────────▶│   Service    │────────▶│   Core Logic     │
│  (main.py)  │         │   (services) │         │   (main.py)      │
└─────────────┘         └──────────────┘         └──────────────────┘
```

**이점:**
- 비즈니스 로직에 대한 단일 진실 공급원
- API와 CLI 간 중복 없음
- 새로운 진입점 추가 용이 (예: WebSocket, GraphQL)
- 진입점과 독립적으로 테스트 가능한 비즈니스 로직

## 종속성

### 내부 종속성
- `langflix/main.py` - `LangFlixPipeline` (핵심 파이프라인 로직)
- `langflix/utils/temp_file_manager.py` - 파일 정리를 위한 TempFileManager (파이프라인에서 내부적으로 사용)
- `langflix/utils/filename_utils.py` - 파일명 정리 (내부적으로 사용)
- `langflix/core/redis_client.py` - 배치 및 큐 작업을 위한 `RedisJobManager`
- `langflix/services/video_pipeline_service.py` - QueueProcessor에서 실제 처리를 위해 사용

### 외부 종속성
- 표준 라이브러리: `logging`, `pathlib`, `typing`, `datetime`

## 일반 작업

### 새 서비스 추가

1. `langflix/services/`에 새 서비스 클래스 생성
2. `VideoPipelineService`와 동일한 패턴 따르기:
   - 필요한 종속성으로 초기화
   - 명확한 메서드 인터페이스 제공
   - 적용 가능한 경우 진행 상황 콜백 지원
   - 표준화된 결과 형식 반환
3. `langflix/services/__init__.py`에서 export
4. 이 문서 업데이트

### VideoPipelineService 수정

1. 변경사항이 하위 호환성을 유지하는지 확인
2. 인터페이스가 변경되는 경우 API와 CLI 모두 업데이트
3. `tests/unit/test_video_pipeline_service.py`에 테스트 추가
4. `tests/integration/test_pipeline_service.py`의 통합 테스트 업데이트

### 진행 상황 추적 추가

1. 서비스 메서드에 `progress_callback` 파라미터 추가
2. 주요 마일스톤에서 콜백 호출
3. 메서드 docstring에 진행률 백분율 문서화
4. 단위 테스트에서 콜백 호출 테스트

## 테스트

### 단위 테스트
- `tests/unit/test_video_pipeline_service.py` - 서비스 단위 테스트
  - 초기화
  - 기본 처리
  - 진행 상황 콜백
  - 에러 처리
  - 결과 추출
- `tests/unit/test_batch_queue_service.py` - BatchQueueService 단위 테스트
  - 다양한 구성으로 배치 생성
  - 배치 상태 계산 (모든 상태 시나리오)
  - 에지 케이스 (episode_name 누락, 빈 경로, 배치 크기 제한)
  - 배치 상태 업데이트
- `tests/unit/test_queue_processor.py` - QueueProcessor 단위 테스트
  - Lock 획득/해제
  - 멈춘 작업 복구
  - Executor 기반 처리 (이벤트 루프 블로킹 방지)
  - 진행 상황 콜백 실패 처리
  - 파일 읽기 실패
  - 우아한 종료

### 통합 테스트
- `tests/integration/test_pipeline_service.py` - 종단 간 서비스 테스트
  - 서비스가 CLI와 동일한 파이프라인 사용
  - 진행 상황 콜백 통합
  - 결과 구조 일관성

## 관련 문서

- [Core 모듈 문서](../core/README_kor.md) - LangFlixPipeline 세부사항
- [API 모듈 문서](../api/README_kor.md) - 서비스의 API 사용
- [문제 해결 가이드](../TROUBLESHOOTING_GUIDE.md)

