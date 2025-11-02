# Monitoring Module Documentation

## Overview

The `langflix/monitoring/` module provides health checking and performance monitoring for LangFlix services.

**Last Updated:** 2025-01-30

## Purpose

This module provides:
- System health checks
- Performance metrics collection
- Real-time monitoring
- Alerting system
- Automated recovery suggestions

## Key Components

### HealthChecker

**Location:** `langflix/monitoring/health_checker.py`

Comprehensive health checking system that monitors:
- System resources (CPU, memory)
- Disk space
- FFmpeg availability
- Python dependencies
- API connectivity
- Cache system
- Database connectivity

**Key Features:**
- Periodic health checks (configurable interval)
- Health status tracking with history
- Health change callbacks
- Recommendations generation

**Usage:**

```python
from langflix.monitoring.health_checker import get_health_checker

checker = get_health_checker()
health = checker.check_system_health()

print(f"Overall status: {health.overall_status}")
for check in health.checks:
    print(f"{check.name}: {check.status} - {check.message}")
```

### SystemHealthChecker

**Location:** `langflix/monitoring/health_checker.py` (lines 559-724)

A lightweight health checking system specifically designed for API health check endpoints. This class provides focused health checks for system components used by production monitoring systems.

**Key Features:**
- Lightweight, fast health checks for production use
- Individual component health verification (database, storage, Redis, TTS)
- Overall health status aggregation
- Designed for API endpoint integration
- Minimal performance impact

**Components Checked:**

1. **Database** (`check_database()`):
   - Verifies database connectivity using `SELECT 1` query
   - Uses `db_manager.session()` context manager for proper resource management
   - Returns `{"status": "healthy", "message": "..."}` or `{"status": "disabled"}` or `{"status": "unhealthy", "message": "..."}`
   - Respects database disabled mode

2. **Storage** (`check_storage()`):
   - Checks storage backend availability by attempting to list files
   - Lightweight operation with minimal overhead
   - Returns storage backend type and status
   - Handles Local and GCS storage backends

3. **Redis** (`check_redis()`):
   - Verifies Redis connectivity via job manager
   - Returns full health dict from `RedisJobManager.health_check()`
   - Includes active jobs count and connection status

4. **TTS** (`check_tts()`):
   - Verifies TTS service configuration
   - Checks API key presence for Gemini or LemonFox providers
   - Does NOT perform actual API calls (to avoid costs)
   - Returns `{"status": "healthy", "message": "..."}` or `{"status": "unhealthy", "message": "..."}` or `{"status": "unknown", "message": "..."}`

**Overall Health** (`get_overall_health()`):
- Aggregates individual component statuses
- Determines overall status: `healthy`, `degraded`, or `unhealthy`
- Returns structured JSON with timestamp
- Used by `/health/detailed` API endpoint

**Usage:**

```python
from langflix.monitoring.health_checker import SystemHealthChecker

checker = SystemHealthChecker()

# Check individual components
db_health = checker.check_database()
storage_health = checker.check_storage()
redis_health = checker.check_redis()
tts_health = checker.check_tts()

# Get overall health
overall = checker.get_overall_health()
print(f"Status: {overall['status']}")
print(f"Components: {overall['components']}")
```

### PerformanceMonitor

**Location:** `langflix/monitoring/performance_monitor.py`

Performance monitoring system that tracks:
- Request metrics (success rate, response time)
- Cache performance (hit rate)
- System metrics (CPU, memory, disk)
- Performance alerts based on thresholds

**Key Features:**
- Real-time metric collection
- Alert threshold configuration
- Performance recommendations
- Historical metric storage

**Usage:**

```python
from langflix.monitoring.performance_monitor import get_performance_monitor

monitor = get_performance_monitor()
monitor.record_request(success=True, response_time=1.2, operation="video_process")

stats = monitor.get_performance_stats()
print(f"Average response time: {stats.average_response_time}s")
```

## Health Status Levels

- `HEALTHY`: System operating normally
- `WARNING`: Degraded performance, attention needed
- `CRITICAL`: Critical issue requiring immediate action
- `UNKNOWN`: Status cannot be determined

## Performance Metrics

### System Metrics
- CPU usage percentage
- Memory usage percentage
- Disk usage and availability
- Process-specific metrics

### Application Metrics
- Total requests
- Success/failure rates
- Average response time
- Cache hit rate
- Error rate

## Common Tasks

### Start Monitoring

```python
from langflix.monitoring.health_checker import start_health_monitoring
from langflix.monitoring.performance_monitor import start_performance_monitoring

start_health_monitoring()
start_performance_monitoring()
```

### Get Health Summary

```python
from langflix.monitoring.health_checker import get_health_summary

summary = get_health_summary()
print(f"Status: {summary['overall_status']}")
print(f"Uptime: {summary['uptime_hours']} hours")
```

### Set Alert Thresholds

```python
from langflix.monitoring.performance_monitor import get_performance_monitor

monitor = get_performance_monitor()
monitor.alert_thresholds = {
    'cpu_usage': 90.0,
    'memory_usage': 95.0,
    'response_time': 10.0
}
```

## API Integration

The `SystemHealthChecker` class is integrated with FastAPI health endpoints in `langflix/api/routes/health.py`:

- `/health/detailed` - Uses `get_overall_health()` to return comprehensive system status
- `/health/database` - Uses `check_database()` for database-specific health
- `/health/storage` - Uses `check_storage()` for storage-specific health
- `/health/redis` - Uses `check_redis()` for Redis-specific health
- `/health/tts` - Uses `check_tts()` for TTS-specific health

## Testing

Comprehensive test coverage is provided in `tests/monitoring/test_health_checker.py`:
- Unit tests for each `SystemHealthChecker` method
- Tests for disabled/enabled database scenarios
- Tests for various TTS provider configurations
- Overall health aggregation tests
- All tests use proper mocking to avoid external dependencies

## Related Modules

- `langflix/api/routes/health.py`: Health check API endpoints using SystemHealthChecker
- `langflix/core/`: Cache manager integration
- `langflix/db/session.py`: Database session management for health checks
- `langflix/storage/factory.py`: Storage backend creation for health checks

