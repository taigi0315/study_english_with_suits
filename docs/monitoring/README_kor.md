# Monitoring 모듈 문서

## 개요

`langflix/monitoring/` 모듈은 LangFlix 서비스를 위한 건강 상태 확인 및 성능 모니터링을 제공합니다.

**최종 업데이트:** 2025-01-30

## 목적

이 모듈은 다음을 제공합니다:
- 시스템 건강 상태 확인
- 성능 메트릭 수집
- 실시간 모니터링
- 경고 시스템
- 자동 복구 제안

## 주요 구성 요소

### HealthChecker

**위치:** `langflix/monitoring/health_checker.py`

다음을 모니터링하는 포괄적인 건강 상태 확인 시스템:
- 시스템 리소스 (CPU, 메모리)
- 디스크 공간
- FFmpeg 가용성
- Python 종속성
- API 연결
- 캐시 시스템
- 데이터베이스 연결

**주요 기능:**
- 주기적 건강 상태 확인 (설정 가능한 간격)
- 건강 상태 추적 및 히스토리
- 건강 상태 변경 콜백
- 권장사항 생성

**사용법:**

```python
from langflix.monitoring.health_checker import get_health_checker

checker = get_health_checker()
health = checker.check_system_health()

print(f"전체 상태: {health.overall_status}")
for check in health.checks:
    print(f"{check.name}: {check.status} - {check.message}")
```

### SystemHealthChecker

**위치:** `langflix/monitoring/health_checker.py` (559-724줄)

API 헬스 체크 엔드포인트에 최적화된 경량 헬스 체크 시스템입니다. 프로덕션 모니터링에서 필요한 시스템 컴포넌트 상태 확인을 제공합니다.

**주요 기능:**
- 프로덕션용 경량·고속 체크
- 개별 컴포넌트 확인(DB, 스토리지, Redis, TTS)
- 전체 상태 집계
- API 엔드포인트 연동
- 성능 영향 최소화

**확인 항목:**

1. **데이터베이스** (`check_database()`):
   - `SELECT 1`로 연결 확인
   - `db_manager.session()`로 리소스 관리
   - `{"status": "healthy", "message": "..."}`, `{"status": "disabled"}`, `{"status": "unhealthy", "message": "..."}` 반환
   - DB 비활성 모드 지원

2. **스토리지** (`check_storage()`):
   - 파일 목록 조회로 백엔드 가용성 확인
   - 최소 오버헤드
   - 백엔드 타입·상태 반환
   - Local/GCS 지원

3. **Redis** (`check_redis()`):
   - Job Manager로 연결 확인
   - `RedisJobManager.health_check()` 결과 반환
   - 활성 잡 수 및 연결 상태 포함

4. **TTS** (`check_tts()`):
   - 설정 확인
   - Gemini/LemonFox API 키 존재 확인
   - 실제 호출 없음(비용 절감)
   - `{"status": "healthy", "message": "..."}`, `{"status": "unhealthy", "message": "..."}`, `{"status": "unknown", "message": "..."}` 반환

**전체 상태** (`get_overall_health()`):
- 컴포넌트별 상태 집계
- `healthy`, `degraded`, `unhealthy` 판정
- 타임스탬프 포함 JSON 반환
- `/health/detailed` API 사용

**사용법:**

```python
from langflix.monitoring.health_checker import SystemHealthChecker

checker = SystemHealthChecker()

# 개별 컴포넌트 확인
db_health = checker.check_database()
storage_health = checker.check_storage()
redis_health = checker.check_redis()
tts_health = checker.check_tts()

# 전체 상태 확인
overall = checker.get_overall_health()
print(f"상태: {overall['status']}")
print(f"컴포넌트: {overall['components']}")
```

### PerformanceMonitor

**위치:** `langflix/monitoring/performance_monitor.py`

다음을 추적하는 성능 모니터링 시스템:
- 요청 메트릭 (성공률, 응답 시간)
- 캐시 성능 (히트율)
- 시스템 메트릭 (CPU, 메모리, 디스크)
- 임계값 기반 성능 경고

**주요 기능:**
- 실시간 메트릭 수집
- 경고 임계값 구성
- 성능 권장사항
- 역사적 메트릭 저장

**사용법:**

```python
from langflix.monitoring.performance_monitor import get_performance_monitor

monitor = get_performance_monitor()
monitor.record_request(success=True, response_time=1.2, operation="video_process")

stats = monitor.get_performance_stats()
print(f"평균 응답 시간: {stats.average_response_time}초")
```

## 건강 상태 레벨

- `HEALTHY`: 시스템 정상 작동
- `WARNING`: 성능 저하, 주의 필요
- `CRITICAL`: 즉시 조치가 필요한 중요한 문제
- `UNKNOWN`: 상태를 확인할 수 없음

## 성능 메트릭

### 시스템 메트릭
- CPU 사용률
- 메모리 사용률
- 디스크 사용량 및 가용성
- 프로세스별 메트릭

### 애플리케이션 메트릭
- 총 요청 수
- 성공/실패율
- 평균 응답 시간
- 캐시 히트율
- 오류율

## 일반적인 작업

### 모니터링 시작

```python
from langflix.monitoring.health_checker import start_health_monitoring
from langflix.monitoring.performance_monitor import start_performance_monitoring

start_health_monitoring()
start_performance_monitoring()
```

### 건강 상태 요약 가져오기

```python
from langflix.monitoring.health_checker import get_health_summary

summary = get_health_summary()
print(f"상태: {summary['overall_status']}")
print(f"가동 시간: {summary['uptime_hours']} 시간")
```

### 경고 임계값 설정

```python
from langflix.monitoring.performance_monitor import get_performance_monitor

monitor = get_performance_monitor()
monitor.alert_thresholds = {
    'cpu_usage': 90.0,
    'memory_usage': 95.0,
    'response_time': 10.0
}
```

## API 통합

`SystemHealthChecker` 클래스는 `langflix/api/routes/health.py`의 FastAPI 헬스 엔드포인트와 통합되어 있습니다:

- `/health/detailed` - 전체 시스템 상태 반환 (`get_overall_health()` 사용)
- `/health/database` - 데이터베이스 상태 확인 (`check_database()` 사용)
- `/health/storage` - 스토리지 상태 확인 (`check_storage()` 사용)
- `/health/redis` - Redis 상태 확인 (`check_redis()` 사용)
- `/health/tts` - TTS 상태 확인 (`check_tts()` 사용)

## 테스트

`tests/monitoring/test_health_checker.py`에 테스트가 포함되어 있습니다:
- 각 `SystemHealthChecker` 메서드 단위 테스트
- DB 비활성/활성 시나리오 테스트
- TTS 설정 테스트
- 전체 상태 집계 테스트
- 외부 의존성 제거용 모킹

## 관련 모듈

- `langflix/api/routes/health.py`: SystemHealthChecker 사용 엔드포인트
- `langflix/core/`: 캐시 관리자 통합
- `langflix/db/session.py`: 헬스 체크용 DB 세션 관리
- `langflix/storage/factory.py`: 헬스 체크용 스토리지 백엔드 생성

