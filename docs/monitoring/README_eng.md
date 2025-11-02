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

## Related Modules

- `langflix/api/`: Health check endpoints
- `langflix/core/`: Cache manager integration

