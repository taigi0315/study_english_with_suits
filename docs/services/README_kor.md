# Services 모듈 문서

## 개요

`langflix/services/` 모듈은 API와 CLI 구현 간에 이전에 중복되었던 코드를 통합하여 비즈니스 로직에 대한 통합 인터페이스를 제공하는 서비스 레이어 클래스를 포함합니다.

**최종 업데이트:** 2025-01-30  
**관련 티켓:** TICKET-001-extract-pipeline-logic

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

### 통합 테스트
- `tests/integration/test_pipeline_service.py` - 종단 간 서비스 테스트
  - 서비스가 CLI와 동일한 파이프라인 사용
  - 진행 상황 콜백 통합
  - 결과 구조 일관성

## 관련 문서

- [Core 모듈 문서](../core/README_kor.md) - LangFlixPipeline 세부사항
- [API 모듈 문서](../api/README_kor.md) - 서비스의 API 사용
- [문제 해결 가이드](../TROUBLESHOOTING_GUIDE.md)

