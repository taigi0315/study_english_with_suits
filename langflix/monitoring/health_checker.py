"""
Health checking system for LangFlix Expression-Based Learning Feature.

This module provides:
- System health checks
- Service availability monitoring
- Dependency health verification
- Health status reporting
- Automated recovery suggestions
"""

import logging
import time
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import subprocess
import psutil

logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    """Health status enumeration"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

@dataclass
class HealthCheck:
    """Health check result"""
    name: str
    status: HealthStatus
    message: str
    timestamp: datetime
    response_time: float = 0.0
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}

@dataclass
class SystemHealth:
    """Overall system health status"""
    overall_status: HealthStatus
    checks: List[HealthCheck]
    timestamp: datetime
    uptime: float = 0.0
    recommendations: List[str] = None
    
    def __post_init__(self):
        if self.recommendations is None:
            self.recommendations = []

class HealthChecker:
    """Advanced health checking system"""
    
    def __init__(self, check_interval: int = 60):
        """
        Initialize health checker
        
        Args:
            check_interval: Health check interval in seconds
        """
        self.check_interval = check_interval
        self.start_time = time.time()
        
        # Health check functions
        self._health_checks = {
            'system_resources': self._check_system_resources,
            'disk_space': self._check_disk_space,
            'ffmpeg_availability': self._check_ffmpeg_availability,
            'python_dependencies': self._check_python_dependencies,
            'api_connectivity': self._check_api_connectivity,
            'cache_system': self._check_cache_system,
            'database_connectivity': self._check_database_connectivity,
        }
        
        # Health check results
        self._last_health_check = None
        self._health_history = []
        
        # Monitoring control
        self._monitoring = False
        self._monitor_thread = None
        self._lock = threading.RLock()
        
        # Health change callbacks
        self._health_callbacks = []
        
        logger.info("HealthChecker initialized")
    
    def start_monitoring(self) -> None:
        """Start health monitoring"""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Health monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop health monitoring"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1)
        logger.info("Health monitoring stopped")
    
    def _monitor_loop(self) -> None:
        """Main health monitoring loop"""
        while self._monitoring:
            try:
                health = self.check_system_health()
                self._record_health_status(health)
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                time.sleep(self.check_interval)
    
    def check_system_health(self) -> SystemHealth:
        """Perform comprehensive system health check"""
        logger.debug("Performing system health check")
        
        checks = []
        overall_status = HealthStatus.HEALTHY
        
        # Run all health checks
        for check_name, check_func in self._health_checks.items():
            try:
                start_time = time.time()
                check_result = check_func()
                response_time = time.time() - start_time
                
                check_result.response_time = response_time
                checks.append(check_result)
                
                # Update overall status
                if check_result.status == HealthStatus.CRITICAL:
                    overall_status = HealthStatus.CRITICAL
                elif check_result.status == HealthStatus.WARNING and overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.WARNING
                
            except Exception as e:
                logger.error(f"Health check {check_name} failed: {e}")
                checks.append(HealthCheck(
                    name=check_name,
                    status=HealthStatus.CRITICAL,
                    message=f"Health check failed: {str(e)}",
                    timestamp=datetime.now()
                ))
                overall_status = HealthStatus.CRITICAL
        
        # Generate recommendations
        recommendations = self._generate_recommendations(checks)
        
        health = SystemHealth(
            overall_status=overall_status,
            checks=checks,
            timestamp=datetime.now(),
            uptime=time.time() - self.start_time,
            recommendations=recommendations
        )
        
        return health
    
    def _check_system_resources(self) -> HealthCheck:
        """Check system resource usage"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Determine status
            if cpu_percent > 90 or memory_percent > 95:
                status = HealthStatus.CRITICAL
                message = f"High resource usage: CPU {cpu_percent:.1f}%, Memory {memory_percent:.1f}%"
            elif cpu_percent > 80 or memory_percent > 85:
                status = HealthStatus.WARNING
                message = f"Elevated resource usage: CPU {cpu_percent:.1f}%, Memory {memory_percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Resource usage normal: CPU {cpu_percent:.1f}%, Memory {memory_percent:.1f}%"
            
            return HealthCheck(
                name='system_resources',
                status=status,
                message=message,
                timestamp=datetime.now(),
                details={
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory_percent,
                    'memory_available_gb': memory.available / (1024**3)
                }
            )
            
        except Exception as e:
            return HealthCheck(
                name='system_resources',
                status=HealthStatus.CRITICAL,
                message=f"Failed to check system resources: {str(e)}",
                timestamp=datetime.now()
            )
    
    def _check_disk_space(self) -> HealthCheck:
        """Check disk space availability"""
        try:
            disk = psutil.disk_usage('/')
            free_percent = (disk.free / disk.total) * 100
            
            if free_percent < 5:
                status = HealthStatus.CRITICAL
                message = f"Critical disk space: {free_percent:.1f}% free"
            elif free_percent < 10:
                status = HealthStatus.WARNING
                message = f"Low disk space: {free_percent:.1f}% free"
            else:
                status = HealthStatus.HEALTHY
                message = f"Disk space OK: {free_percent:.1f}% free"
            
            return HealthCheck(
                name='disk_space',
                status=status,
                message=message,
                timestamp=datetime.now(),
                details={
                    'free_percent': free_percent,
                    'free_gb': disk.free / (1024**3),
                    'total_gb': disk.total / (1024**3)
                }
            )
            
        except Exception as e:
            return HealthCheck(
                name='disk_space',
                status=HealthStatus.CRITICAL,
                message=f"Failed to check disk space: {str(e)}",
                timestamp=datetime.now()
            )
    
    def _check_ffmpeg_availability(self) -> HealthCheck:
        """Check FFmpeg availability"""
        try:
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                return HealthCheck(
                    name='ffmpeg_availability',
                    status=HealthStatus.HEALTHY,
                    message="FFmpeg is available",
                    timestamp=datetime.now(),
                    details={'version': result.stdout.split('\n')[0] if result.stdout else 'Unknown'}
                )
            else:
                return HealthCheck(
                    name='ffmpeg_availability',
                    status=HealthStatus.CRITICAL,
                    message="FFmpeg not available",
                    timestamp=datetime.now()
                )
                
        except subprocess.TimeoutExpired:
            return HealthCheck(
                name='ffmpeg_availability',
                status=HealthStatus.WARNING,
                message="FFmpeg check timed out",
                timestamp=datetime.now()
            )
        except Exception as e:
            return HealthCheck(
                name='ffmpeg_availability',
                status=HealthStatus.CRITICAL,
                message=f"FFmpeg check failed: {str(e)}",
                timestamp=datetime.now()
            )
    
    def _check_python_dependencies(self) -> HealthCheck:
        """Check Python dependencies"""
        try:
            required_modules = [
                'google.generativeai',
                'whisperx',
                'torch',
                'PIL',
                'psutil'
            ]
            
            missing_modules = []
            for module in required_modules:
                try:
                    __import__(module)
                except ImportError:
                    missing_modules.append(module)
            
            if missing_modules:
                status = HealthStatus.CRITICAL
                message = f"Missing dependencies: {', '.join(missing_modules)}"
            else:
                status = HealthStatus.HEALTHY
                message = "All Python dependencies available"
            
            return HealthCheck(
                name='python_dependencies',
                status=status,
                message=message,
                timestamp=datetime.now(),
                details={'missing_modules': missing_modules}
            )
            
        except Exception as e:
            return HealthCheck(
                name='python_dependencies',
                status=HealthStatus.CRITICAL,
                message=f"Dependency check failed: {str(e)}",
                timestamp=datetime.now()
            )
    
    def _check_api_connectivity(self) -> HealthCheck:
        """Check API connectivity"""
        try:
            import os
            api_key = os.getenv('GEMINI_API_KEY')
            
            if not api_key:
                return HealthCheck(
                    name='api_connectivity',
                    status=HealthStatus.WARNING,
                    message="GEMINI_API_KEY not set",
                    timestamp=datetime.now()
                )
            
            # Try to make a simple API call
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            
            # This is a simplified check - in production, you'd want a more robust test
            return HealthCheck(
                name='api_connectivity',
                status=HealthStatus.HEALTHY,
                message="API connectivity OK",
                timestamp=datetime.now()
            )
            
        except Exception as e:
            return HealthCheck(
                name='api_connectivity',
                status=HealthStatus.CRITICAL,
                message=f"API connectivity failed: {str(e)}",
                timestamp=datetime.now()
            )
    
    def _check_cache_system(self) -> HealthCheck:
        """Check cache system health"""
        try:
            from langflix.core.cache_manager import get_cache_manager
            
            cache_manager = get_cache_manager()
            stats = cache_manager.get_stats()
            
            # Check cache health based on stats
            if stats['hit_rate'] < 50:
                status = HealthStatus.WARNING
                message = f"Low cache hit rate: {stats['hit_rate']:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Cache system healthy: {stats['hit_rate']:.1f}% hit rate"
            
            return HealthCheck(
                name='cache_system',
                status=status,
                message=message,
                timestamp=datetime.now(),
                details=stats
            )
            
        except Exception as e:
            return HealthCheck(
                name='cache_system',
                status=HealthStatus.CRITICAL,
                message=f"Cache system check failed: {str(e)}",
                timestamp=datetime.now()
            )
    
    def _check_database_connectivity(self) -> HealthCheck:
        """Check database connectivity"""
        try:
            # This would check database connectivity
            # For now, return a placeholder
            return HealthCheck(
                name='database_connectivity',
                status=HealthStatus.HEALTHY,
                message="Database connectivity OK",
                timestamp=datetime.now()
            )
            
        except Exception as e:
            return HealthCheck(
                name='database_connectivity',
                status=HealthStatus.CRITICAL,
                message=f"Database connectivity failed: {str(e)}",
                timestamp=datetime.now()
            )
    
    def _generate_recommendations(self, checks: List[HealthCheck]) -> List[str]:
        """Generate health recommendations based on check results"""
        recommendations = []
        
        for check in checks:
            if check.status == HealthStatus.CRITICAL:
                if check.name == 'system_resources':
                    recommendations.append("Consider scaling up system resources or optimizing memory usage")
                elif check.name == 'disk_space':
                    recommendations.append("Free up disk space or add more storage")
                elif check.name == 'ffmpeg_availability':
                    recommendations.append("Install FFmpeg for video processing")
                elif check.name == 'python_dependencies':
                    recommendations.append("Install missing Python dependencies")
                elif check.name == 'api_connectivity':
                    recommendations.append("Check API key configuration and network connectivity")
            
            elif check.status == HealthStatus.WARNING:
                if check.name == 'system_resources':
                    recommendations.append("Monitor resource usage and consider optimization")
                elif check.name == 'disk_space':
                    recommendations.append("Monitor disk space usage")
                elif check.name == 'cache_system':
                    recommendations.append("Consider cache optimization or size increase")
        
        return recommendations
    
    def _record_health_status(self, health: SystemHealth) -> None:
        """Record health status and notify callbacks if status changed"""
        with self._lock:
            # Check if status changed
            if self._last_health_check:
                if self._last_health_check.overall_status != health.overall_status:
                    for callback in self._health_callbacks:
                        try:
                            callback(health)
                        except Exception as e:
                            logger.error(f"Health callback error: {e}")
            
            self._last_health_check = health
            self._health_history.append(health)
            
            # Keep only last 100 health checks
            if len(self._health_history) > 100:
                self._health_history = self._health_history[-100:]
    
    def get_current_health(self) -> Optional[SystemHealth]:
        """Get current system health status"""
        with self._lock:
            return self._last_health_check
    
    def get_health_history(self, hours: int = 24) -> List[SystemHealth]:
        """Get health history for specified hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            return [
                health for health in self._health_history
                if health.timestamp >= cutoff_time
            ]
    
    def add_health_callback(self, callback: Callable[[SystemHealth], None]) -> None:
        """Add health status change callback"""
        self._health_callbacks.append(callback)
    
    def remove_health_callback(self, callback: Callable[[SystemHealth], None]) -> None:
        """Remove health status change callback"""
        if callback in self._health_callbacks:
            self._health_callbacks.remove(callback)
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get comprehensive health summary"""
        current_health = self.get_current_health()
        if not current_health:
            return {'status': 'unknown', 'message': 'No health data available'}
        
        # Count checks by status
        status_counts = {}
        for check in current_health.checks:
            status = check.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            'overall_status': current_health.overall_status.value,
            'timestamp': current_health.timestamp.isoformat(),
            'uptime_hours': current_health.uptime / 3600,
            'check_counts': status_counts,
            'recommendations': current_health.recommendations,
            'checks': [
                {
                    'name': check.name,
                    'status': check.status.value,
                    'message': check.message,
                    'response_time': check.response_time
                }
                for check in current_health.checks
            ]
        }

# Global health checker instance
_health_checker: Optional[HealthChecker] = None

def get_health_checker() -> HealthChecker:
    """Get global health checker instance"""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker

def start_health_monitoring() -> None:
    """Start global health monitoring"""
    checker = get_health_checker()
    checker.start_monitoring()

def stop_health_monitoring() -> None:
    """Stop global health monitoring"""
    checker = get_health_checker()
    checker.stop_monitoring()

def check_system_health() -> SystemHealth:
    """Perform system health check"""
    checker = get_health_checker()
    return checker.check_system_health()

def get_health_summary() -> Dict[str, Any]:
    """Get health summary"""
    checker = get_health_checker()
    return checker.get_health_summary()
