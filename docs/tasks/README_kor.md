# 작업 모듈

## 개요

`langflix/tasks/` 모듈은 Celery를 사용한 백그라운드 작업 처리를 제공합니다. 비동기 비디오 처리, 교육용 슬라이드 생성, 파일 정리 작업을 가능하게 합니다.

**목적:**
- 장기 실행 작업을 위한 비동기 비디오 처리
- 진행 상황 추적이 있는 백그라운드 작업 실행
- Redis를 사용한 작업 큐 관리
- 예약된 정리 작업

**사용 시기:**
- API를 통해 비디오를 비동기로 처리할 때
- 예약된 유지보수 작업을 실행할 때
- 백그라운드 작업 처리를 구현할 때

## 파일 목록

### `celery_app.py`
Celery 애플리케이션 설정 및 초기화.

**주요 구성 요소:**
- `celery_app` - 메인 Celery 애플리케이션 인스턴스
- Redis 브로커 및 결과 백엔드 설정
- 작업 직렬화 설정
- 시간 제한 및 워커 설정

### `tasks.py`
백그라운드 작업 정의.

**주요 작업:**
- `process_video_content()` - 표현식 기반 학습을 위한 비디오 콘텐츠 처리
- `generate_educational_slides()` - 콘텐츠 데이터에서 교육용 슬라이드 생성
- `cleanup_old_files()` - 오래된 임시 파일 정리

## 주요 구성 요소

### Celery 애플리케이션 설정

Celery 애플리케이션은 Redis를 브로커 및 결과 백엔드로 사용하도록 구성됩니다.

**설정 세부사항:**
- **브로커**: `localhost:6379/0`의 Redis
- **결과 백엔드**: 작업 결과용 Redis
- **직렬화**: JSON 형식
- **시간 제한**: 30분 하드 제한, 25분 소프트 제한
- **워커 설정**: 프리페치 배수 1, 늦은 확인

### 비디오 처리 작업

비디오 콘텐츠를 표현식 기반 학습을 위해 처리하는 작업입니다.

**기능:**
- `update_state()`를 통한 진행 상황 추적
- 상태 업데이트: PROGRESS, SUCCESS, FAILURE
- 예외 로깅이 있는 오류 처리
- 진행 상황 보고를 위한 작업 메타데이터

### 교육용 슬라이드 생성 작업

콘텐츠 데이터에서 교육용 슬라이드를 생성하는 작업입니다.

### 파일 정리 작업

오래된 임시 파일을 정리하는 작업입니다.

## 구현 세부사항

### 작업 상태 관리

작업은 진행 상황 추적을 위해 Celery의 상태 관리를 사용합니다.

### 오류 처리

작업은 포괄적인 오류 처리를 구현합니다.

## 의존성

**외부 라이브러리:**
- `celery` - 분산 작업 큐
- `redis` - 메시지 브로커 및 결과 백엔드

**인프라:**
- Redis 서버 (브로커 및 결과 백엔드에 필요)
- Celery 워커 프로세스

## 일반적인 작업

### Celery 워커 시작

```bash
# 워커 시작
celery -A langflix.tasks.celery_app worker --loglevel=info

# 동시성과 함께 시작
celery -A langflix.tasks.celery_app worker --loglevel=info --concurrency=4
```

## 주의사항 및 참고사항

### 중요 고려사항

1. **Redis 연결:**
   - 워커를 시작하기 전에 Redis가 실행 중인지 확인하세요
   - 기본 연결: `localhost:6379/0`
   - 필요시 환경 변수를 통해 Redis URL 구성

2. **작업 시간 제한:**
   - 하드 제한: 30분 (초과 시 작업 종료)
   - 소프트 제한: 25분 (SoftTimeLimitExceeded 예외)
   - 비디오 처리 요구사항에 따라 조정

3. **현재 구현 상태:**
   - 현재 작업 구현은 TODO 주석이 있는 플레이스홀더입니다
   - 전체 구현은 `VideoPipelineService`와 통합해야 합니다

## 관련 문서

- [Services Module](../services/README_eng.md) - 비즈니스 로직 서비스
- [API Module](../api/README_eng.md) - 작업을 사용하는 API 엔드포인트
- [Core Module](../core/README_eng.md) - 핵심 처리 로직

