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

## 관련 모듈

- `langflix/api/`: 건강 상태 확인 엔드포인트
- `langflix/core/`: 캐시 관리자 통합

