"""
Performance monitoring system for LangFlix Expression-Based Learning Feature.

This module provides:
- Performance metrics collection
- Real-time monitoring
- Performance analysis
- Alerting system
- Performance optimization recommendations
"""

import logging
import time
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json
import psutil

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetric:
    """Performance metric data"""
    name: str
    value: float
    timestamp: datetime
    unit: str = ""
    tags: Dict[str, str] = field(default_factory=dict)

@dataclass
class PerformanceAlert:
    """Performance alert"""
    metric_name: str
    threshold: float
    current_value: float
    severity: str  # low, medium, high, critical
    message: str
    timestamp: datetime

@dataclass
class PerformanceStats:
    """Performance statistics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    peak_memory_usage: float = 0.0
    peak_cpu_usage: float = 0.0
    cache_hit_rate: float = 0.0
    error_rate: float = 0.0

class PerformanceMonitor:
    """Advanced performance monitoring system"""
    
    def __init__(
        self,
        monitoring_interval: int = 30,
        max_metrics_history: int = 1000,
        alert_thresholds: Optional[Dict[str, float]] = None
    ):
        """
        Initialize performance monitor
        
        Args:
            monitoring_interval: Monitoring interval in seconds
            max_metrics_history: Maximum number of metrics to keep in history
            alert_thresholds: Custom alert thresholds
        """
        self.monitoring_interval = monitoring_interval
        self.max_metrics_history = max_metrics_history
        self.alert_thresholds = alert_thresholds or self._get_default_thresholds()
        
        # Metrics storage
        self.metrics_history = defaultdict(lambda: deque(maxlen=max_metrics_history))
        self.current_metrics = {}
        self.alerts = []
        
        # Statistics
        self.stats = PerformanceStats()
        
        # Monitoring control
        self._monitoring = False
        self._monitor_thread = None
        self._lock = threading.RLock()
        
        # Alert callbacks
        self._alert_callbacks = []
        
        logger.info("PerformanceMonitor initialized")
    
    def _get_default_thresholds(self) -> Dict[str, float]:
        """Get default alert thresholds"""
        return {
            'cpu_usage': 80.0,  # CPU usage percentage
            'memory_usage': 85.0,  # Memory usage percentage
            'response_time': 5.0,  # Response time in seconds
            'error_rate': 10.0,  # Error rate percentage
            'cache_hit_rate': 50.0,  # Cache hit rate percentage (minimum)
            'disk_usage': 90.0,  # Disk usage percentage
        }
    
    def start_monitoring(self) -> None:
        """Start performance monitoring"""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Performance monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop performance monitoring"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1)
        logger.info("Performance monitoring stopped")
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop"""
        while self._monitoring:
            try:
                self._collect_system_metrics()
                self._check_alert_thresholds()
                time.sleep(self.monitoring_interval)
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                time.sleep(self.monitoring_interval)
    
    def _collect_system_metrics(self) -> None:
        """Collect system performance metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self._record_metric('cpu_usage', cpu_percent, '%')
            
            # Memory usage
            memory = psutil.virtual_memory()
            self._record_metric('memory_usage', memory.percent, '%')
            self._record_metric('memory_available', memory.available / (1024**3), 'GB')
            
            # Disk usage
            disk = psutil.disk_usage('/')
            self._record_metric('disk_usage', (disk.used / disk.total) * 100, '%')
            self._record_metric('disk_available', disk.free / (1024**3), 'GB')
            
            # Process-specific metrics
            process = psutil.Process()
            self._record_metric('process_memory', process.memory_info().rss / (1024**2), 'MB')
            self._record_metric('process_cpu', process.cpu_percent(), '%')
            
            # Update peak values
            with self._lock:
                self.stats.peak_memory_usage = max(self.stats.peak_memory_usage, memory.percent)
                self.stats.peak_cpu_usage = max(self.stats.peak_cpu_usage, cpu_percent)
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
    
    def _record_metric(self, name: str, value: float, unit: str = "", tags: Dict[str, str] = None) -> None:
        """Record a performance metric"""
        metric = PerformanceMetric(
            name=name,
            value=value,
            timestamp=datetime.now(),
            unit=unit,
            tags=tags or {}
        )
        
        with self._lock:
            self.metrics_history[name].append(metric)
            self.current_metrics[name] = metric
    
    def _check_alert_thresholds(self) -> None:
        """Check if any metrics exceed alert thresholds"""
        for metric_name, threshold in self.alert_thresholds.items():
            if metric_name in self.current_metrics:
                current_value = self.current_metrics[metric_name].value
                
                if current_value > threshold:
                    self._trigger_alert(metric_name, threshold, current_value)
    
    def _trigger_alert(self, metric_name: str, threshold: float, current_value: float) -> None:
        """Trigger a performance alert"""
        # Determine severity
        severity = self._determine_severity(metric_name, threshold, current_value)
        
        alert = PerformanceAlert(
            metric_name=metric_name,
            threshold=threshold,
            current_value=current_value,
            severity=severity,
            message=f"{metric_name} exceeded threshold: {current_value:.2f} > {threshold:.2f}",
            timestamp=datetime.now()
        )
        
        with self._lock:
            self.alerts.append(alert)
            # Keep only last 100 alerts
            if len(self.alerts) > 100:
                self.alerts = self.alerts[-100:]
        
        # Call alert callbacks
        for callback in self._alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")
        
        logger.warning(f"Performance alert: {alert.message}")
    
    def _determine_severity(self, metric_name: str, threshold: float, current_value: float) -> str:
        """Determine alert severity based on how much the threshold is exceeded"""
        excess_ratio = current_value / threshold
        
        if excess_ratio >= 2.0:
            return "critical"
        elif excess_ratio >= 1.5:
            return "high"
        elif excess_ratio >= 1.2:
            return "medium"
        else:
            return "low"
    
    def record_request(self, success: bool, response_time: float, operation: str = "") -> None:
        """Record a request metric"""
        with self._lock:
            self.stats.total_requests += 1
            if success:
                self.stats.successful_requests += 1
            else:
                self.stats.failed_requests += 1
            
            # Update average response time
            if self.stats.total_requests > 0:
                self.stats.average_response_time = (
                    (self.stats.average_response_time * (self.stats.total_requests - 1) + response_time) /
                    self.stats.total_requests
                )
            
            # Update error rate
            self.stats.error_rate = (self.stats.failed_requests / self.stats.total_requests) * 100
        
        # Record response time metric
        self._record_metric('response_time', response_time, 's', {'operation': operation})
        
        # Record success/failure
        self._record_metric('request_success', 1 if success else 0, '', {'operation': operation})
    
    def record_cache_metrics(self, hits: int, misses: int) -> None:
        """Record cache performance metrics"""
        total = hits + misses
        if total > 0:
            hit_rate = (hits / total) * 100
            self._record_metric('cache_hit_rate', hit_rate, '%')
            
            with self._lock:
                self.stats.cache_hit_rate = hit_rate
    
    def get_current_metrics(self) -> Dict[str, PerformanceMetric]:
        """Get current performance metrics"""
        with self._lock:
            return self.current_metrics.copy()
    
    def get_metrics_history(self, metric_name: str, duration_minutes: int = 60) -> List[PerformanceMetric]:
        """Get metrics history for a specific metric"""
        cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
        
        with self._lock:
            return [
                metric for metric in self.metrics_history[metric_name]
                if metric.timestamp >= cutoff_time
            ]
    
    def get_performance_stats(self) -> PerformanceStats:
        """Get current performance statistics"""
        with self._lock:
            return PerformanceStats(
                total_requests=self.stats.total_requests,
                successful_requests=self.stats.successful_requests,
                failed_requests=self.stats.failed_requests,
                average_response_time=self.stats.average_response_time,
                peak_memory_usage=self.stats.peak_memory_usage,
                peak_cpu_usage=self.stats.peak_cpu_usage,
                cache_hit_rate=self.stats.cache_hit_rate,
                error_rate=self.stats.error_rate
            )
    
    def get_recent_alerts(self, hours: int = 24) -> List[PerformanceAlert]:
        """Get recent alerts"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            return [
                alert for alert in self.alerts
                if alert.timestamp >= cutoff_time
            ]
    
    def add_alert_callback(self, callback: Callable[[PerformanceAlert], None]) -> None:
        """Add alert callback function"""
        self._alert_callbacks.append(callback)
    
    def remove_alert_callback(self, callback: Callable[[PerformanceAlert], None]) -> None:
        """Remove alert callback function"""
        if callback in self._alert_callbacks:
            self._alert_callbacks.remove(callback)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        stats = self.get_performance_stats()
        recent_alerts = self.get_recent_alerts(1)  # Last hour
        
        # Get current system metrics
        current_metrics = self.get_current_metrics()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'stats': {
                'total_requests': stats.total_requests,
                'success_rate': (stats.successful_requests / max(stats.total_requests, 1)) * 100,
                'average_response_time': stats.average_response_time,
                'error_rate': stats.error_rate,
                'cache_hit_rate': stats.cache_hit_rate
            },
            'system_metrics': {
                metric_name: {
                    'value': metric.value,
                    'unit': metric.unit,
                    'timestamp': metric.timestamp.isoformat()
                }
                for metric_name, metric in current_metrics.items()
            },
            'alerts': {
                'total_recent': len(recent_alerts),
                'by_severity': {
                    severity: len([a for a in recent_alerts if a.severity == severity])
                    for severity in ['low', 'medium', 'high', 'critical']
                }
            },
            'recommendations': self._generate_recommendations(stats, current_metrics)
        }
    
    def _generate_recommendations(self, stats: PerformanceStats, current_metrics: Dict[str, PerformanceMetric]) -> List[str]:
        """Generate performance optimization recommendations"""
        recommendations = []
        
        # High error rate
        if stats.error_rate > 5:
            recommendations.append("High error rate detected - investigate error causes")
        
        # Low cache hit rate
        if stats.cache_hit_rate < 70:
            recommendations.append("Low cache hit rate - consider increasing cache size or TTL")
        
        # High response time
        if stats.average_response_time > 2:
            recommendations.append("High average response time - consider performance optimization")
        
        # High memory usage
        if 'memory_usage' in current_metrics and current_metrics['memory_usage'].value > 80:
            recommendations.append("High memory usage - consider memory optimization")
        
        # High CPU usage
        if 'cpu_usage' in current_metrics and current_metrics['cpu_usage'].value > 80:
            recommendations.append("High CPU usage - consider load balancing or optimization")
        
        return recommendations

# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None

def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor

def start_performance_monitoring() -> None:
    """Start global performance monitoring"""
    monitor = get_performance_monitor()
    monitor.start_monitoring()

def stop_performance_monitoring() -> None:
    """Stop global performance monitoring"""
    monitor = get_performance_monitor()
    monitor.stop_monitoring()

def record_request_metric(success: bool, response_time: float, operation: str = "") -> None:
    """Record request metric"""
    monitor = get_performance_monitor()
    monitor.record_request(success, response_time, operation)

def record_cache_metric(hits: int, misses: int) -> None:
    """Record cache metric"""
    monitor = get_performance_monitor()
    monitor.record_cache_metrics(hits, misses)
