"""
Advanced error handling and recovery system for LangFlix Expression-Based Learning Feature.

This module provides:
- Graceful error handling
- Automatic retry mechanisms
- Fallback strategies
- Error reporting
- Recovery suggestions
"""

import logging
import time
import traceback
from typing import Dict, Any, List, Optional, Callable, Type, Union
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import functools

logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """Error categories"""
    SYSTEM = "system"
    NETWORK = "network"
    PROCESSING = "processing"
    VALIDATION = "validation"
    RESOURCE = "resource"
    UNKNOWN = "unknown"

@dataclass
class ErrorContext:
    """Error context information"""
    operation: str
    component: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    additional_data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.additional_data is None:
            self.additional_data = {}

@dataclass
class ErrorReport:
    """Error report with context and recovery information"""
    error_id: str
    error_type: str
    message: str
    severity: ErrorSeverity
    category: ErrorCategory
    context: ErrorContext
    timestamp: datetime
    stack_trace: str
    recovery_suggestions: List[str]
    retry_count: int = 0
    resolved: bool = False

class RetryConfig:
    """Retry configuration"""
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_backoff: bool = True,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_backoff = exponential_backoff
        self.jitter = jitter

class ErrorHandler:
    """Advanced error handling and recovery system"""
    
    def __init__(self):
        """Initialize error handler"""
        self.error_reports = []
        self.error_callbacks = []
        self.retry_configs = {}
        self.fallback_strategies = {}
        
        # Initialize default retry configurations
        self._initialize_default_retry_configs()
        
        logger.info("ErrorHandler initialized")
    
    def _initialize_default_retry_configs(self) -> None:
        """Initialize default retry configurations for different error types"""
        self.retry_configs = {
            'network': RetryConfig(max_attempts=5, base_delay=1.0, max_delay=30.0),
            'api': RetryConfig(max_attempts=3, base_delay=2.0, max_delay=60.0),
            'processing': RetryConfig(max_attempts=2, base_delay=5.0, max_delay=120.0),
            'validation': RetryConfig(max_attempts=1, base_delay=0.0, max_delay=0.0),
            'system': RetryConfig(max_attempts=1, base_delay=0.0, max_delay=0.0),
        }
    
    def handle_error(
        self,
        error: Exception,
        context: ErrorContext,
        retry: bool = True,
        fallback: bool = True
    ) -> ErrorReport:
        """
        Handle an error with context and recovery options
        
        Args:
            error: The exception that occurred
            context: Error context information
            retry: Whether to attempt retry
            fallback: Whether to attempt fallback
            
        Returns:
            ErrorReport with handling details
        """
        # Create error report
        error_report = self._create_error_report(error, context)
        
        # Log the error
        self._log_error(error_report)
        
        # Store error report
        self.error_reports.append(error_report)
        
        # Notify callbacks
        for callback in self.error_callbacks:
            try:
                callback(error_report)
            except Exception as e:
                logger.error(f"Error callback failed: {e}")
        
        # Attempt recovery if configured
        if retry and self._should_retry(error, context):
            self._attempt_retry(error, context, error_report)
        
        if fallback and self._has_fallback(error, context):
            self._attempt_fallback(error, context, error_report)
        
        return error_report
    
    def _create_error_report(self, error: Exception, context: ErrorContext) -> ErrorReport:
        """Create error report from exception and context"""
        error_id = f"err_{int(time.time() * 1000)}"
        error_type = type(error).__name__
        message = str(error)
        
        # Determine severity and category
        severity = self._determine_severity(error, context)
        category = self._determine_category(error, context)
        
        # Get recovery suggestions
        recovery_suggestions = self._get_recovery_suggestions(error, context)
        
        # Get stack trace
        stack_trace = traceback.format_exc()
        
        return ErrorReport(
            error_id=error_id,
            error_type=error_type,
            message=message,
            severity=severity,
            category=category,
            context=context,
            timestamp=datetime.now(),
            stack_trace=stack_trace,
            recovery_suggestions=recovery_suggestions
        )
    
    def _determine_severity(self, error: Exception, context: ErrorContext) -> ErrorSeverity:
        """Determine error severity based on error type and context"""
        error_type = type(error).__name__
        
        # Critical errors
        if error_type in ['SystemExit', 'KeyboardInterrupt', 'MemoryError']:
            return ErrorSeverity.CRITICAL
        
        # High severity errors
        if error_type in ['ConnectionError', 'TimeoutError', 'FileNotFoundError']:
            return ErrorSeverity.HIGH
        
        # Medium severity errors
        if error_type in ['ValueError', 'TypeError', 'AttributeError']:
            return ErrorSeverity.MEDIUM
        
        # Low severity errors
        if error_type in ['Warning', 'UserWarning']:
            return ErrorSeverity.LOW
        
        # Default to medium
        return ErrorSeverity.MEDIUM
    
    def _determine_category(self, error: Exception, context: ErrorContext) -> ErrorCategory:
        """Determine error category based on error type and context"""
        error_type = type(error).__name__
        
        if error_type in ['ConnectionError', 'TimeoutError', 'URLError']:
            return ErrorCategory.NETWORK
        
        if error_type in ['ValueError', 'TypeError', 'ValidationError']:
            return ErrorCategory.VALIDATION
        
        if error_type in ['MemoryError', 'OSError', 'IOError']:
            return ErrorCategory.RESOURCE
        
        if error_type in ['ProcessingError', 'VideoProcessingError']:
            return ErrorCategory.PROCESSING
        
        if error_type in ['SystemError', 'RuntimeError']:
            return ErrorCategory.SYSTEM
        
        return ErrorCategory.UNKNOWN
    
    def _get_recovery_suggestions(self, error: Exception, context: ErrorContext) -> List[str]:
        """Get recovery suggestions based on error type and context"""
        suggestions = []
        error_type = type(error).__name__
        category = self._determine_category(error, context)
        
        if category == ErrorCategory.NETWORK:
            suggestions.extend([
                "Check network connectivity",
                "Verify API endpoints are accessible",
                "Check firewall settings",
                "Try again in a few minutes"
            ])
        
        elif category == ErrorCategory.RESOURCE:
            suggestions.extend([
                "Check available disk space",
                "Check available memory",
                "Close other applications to free resources",
                "Restart the application"
            ])
        
        elif category == ErrorCategory.VALIDATION:
            suggestions.extend([
                "Check input data format",
                "Verify required fields are present",
                "Check data type compatibility",
                "Review validation rules"
            ])
        
        elif category == ErrorCategory.PROCESSING:
            suggestions.extend([
                "Check input file format",
                "Verify file permissions",
                "Check processing parameters",
                "Try with different input data"
            ])
        
        elif category == ErrorCategory.SYSTEM:
            suggestions.extend([
                "Check system requirements",
                "Verify all dependencies are installed",
                "Check system logs",
                "Contact system administrator"
            ])
        
        return suggestions
    
    def _should_retry(self, error: Exception, context: ErrorContext) -> bool:
        """Determine if error should be retried"""
        category = self._determine_category(error, context)
        severity = self._determine_severity(error, context)
        
        # Don't retry critical errors
        if severity == ErrorSeverity.CRITICAL:
            return False
        
        # Don't retry validation errors
        if category == ErrorCategory.VALIDATION:
            return False
        
        # Retry network and processing errors
        if category in [ErrorCategory.NETWORK, ErrorCategory.PROCESSING]:
            return True
        
        return False
    
    def _has_fallback(self, error: Exception, context: ErrorContext) -> bool:
        """Check if fallback strategy exists for error"""
        category = self._determine_category(error, context)
        return category in self.fallback_strategies
    
    def _attempt_retry(self, error: Exception, context: ErrorContext, error_report: ErrorReport) -> None:
        """Attempt to retry the operation"""
        category = self._determine_category(error, context)
        retry_config = self.retry_configs.get(category)
        
        if not retry_config:
            return
        
        error_report.retry_count += 1
        
        if error_report.retry_count <= retry_config.max_attempts:
            delay = self._calculate_retry_delay(error_report.retry_count, retry_config)
            logger.info(f"Retrying operation in {delay:.2f} seconds (attempt {error_report.retry_count})")
            time.sleep(delay)
        else:
            logger.warning(f"Max retry attempts ({retry_config.max_attempts}) exceeded")
    
    def _attempt_fallback(self, error: Exception, context: ErrorContext, error_report: ErrorReport) -> None:
        """Attempt fallback strategy"""
        category = self._determine_category(error, context)
        fallback_strategy = self.fallback_strategies.get(category)
        
        if fallback_strategy:
            try:
                logger.info(f"Attempting fallback strategy for {category.value} error")
                fallback_strategy(error, context)
                error_report.resolved = True
            except Exception as e:
                logger.error(f"Fallback strategy failed: {e}")
    
    def _calculate_retry_delay(self, attempt: int, config: RetryConfig) -> float:
        """Calculate retry delay with exponential backoff and jitter"""
        if config.exponential_backoff:
            delay = config.base_delay * (2 ** (attempt - 1))
        else:
            delay = config.base_delay
        
        delay = min(delay, config.max_delay)
        
        if config.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)
        
        return delay
    
    def _log_error(self, error_report: ErrorReport) -> None:
        """Log error with appropriate level"""
        log_message = f"Error {error_report.error_id}: {error_report.message}"
        
        if error_report.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message)
        elif error_report.severity == ErrorSeverity.HIGH:
            logger.error(log_message)
        elif error_report.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message)
        else:
            logger.info(log_message)
    
    def add_error_callback(self, callback: Callable[[ErrorReport], None]) -> None:
        """Add error callback function"""
        self.error_callbacks.append(callback)
    
    def remove_error_callback(self, callback: Callable[[ErrorReport], None]) -> None:
        """Remove error callback function"""
        if callback in self.error_callbacks:
            self.error_callbacks.remove(callback)
    
    def set_retry_config(self, category: ErrorCategory, config: RetryConfig) -> None:
        """Set retry configuration for error category"""
        self.retry_configs[category] = config
    
    def set_fallback_strategy(self, category: ErrorCategory, strategy: Callable) -> None:
        """Set fallback strategy for error category"""
        self.fallback_strategies[category] = strategy
    
    def get_error_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Get error statistics for specified hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_errors = [
            error for error in self.error_reports
            if error.timestamp >= cutoff_time
        ]
        
        if not recent_errors:
            return {'total_errors': 0}
        
        # Count by severity
        severity_counts = {}
        for error in recent_errors:
            severity = error.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # Count by category
        category_counts = {}
        for error in recent_errors:
            category = error.category.value
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Count by component
        component_counts = {}
        for error in recent_errors:
            component = error.context.component
            component_counts[component] = component_counts.get(component, 0) + 1
        
        return {
            'total_errors': len(recent_errors),
            'by_severity': severity_counts,
            'by_category': category_counts,
            'by_component': component_counts,
            'resolved_errors': len([e for e in recent_errors if e.resolved]),
            'resolution_rate': len([e for e in recent_errors if e.resolved]) / len(recent_errors)
        }

def handle_error_decorator(
    context: ErrorContext,
    retry: bool = True,
    fallback: bool = True
):
    """Decorator for automatic error handling"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_handler = get_error_handler()
                error_report = error_handler.handle_error(e, context, retry, fallback)
                raise
        return wrapper
    return decorator

def retry_on_error(
    max_attempts: int = 3,
    delay: float = 1.0,
    exceptions: tuple = (Exception,)
):
    """Decorator for automatic retry on error"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(delay * (2 ** attempt))  # Exponential backoff
                    else:
                        break
            
            raise last_exception
        return wrapper
    return decorator

# Global error handler instance
_error_handler: Optional[ErrorHandler] = None

def get_error_handler() -> ErrorHandler:
    """Get global error handler instance"""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler

def handle_error(
    error: Exception,
    context: ErrorContext,
    retry: bool = True,
    fallback: bool = True
) -> ErrorReport:
    """
    Convenience function for error handling
    
    Args:
        error: The exception that occurred
        context: Error context information
        retry: Whether to attempt retry
        fallback: Whether to attempt fallback
        
    Returns:
        ErrorReport with handling details
    """
    handler = get_error_handler()
    return handler.handle_error(error, context, retry, fallback)
