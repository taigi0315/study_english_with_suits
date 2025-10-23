"""
Memory management utilities for LangFlix Expression-Based Learning Feature.

This module provides:
- Memory usage monitoring
- Garbage collection optimization
- Memory-efficient data structures
- Resource cleanup
- Memory leak detection
"""

import gc
import logging
import psutil
import sys
import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from contextlib import contextmanager
from functools import wraps
import threading

logger = logging.getLogger(__name__)

@dataclass
class MemoryStats:
    """Memory usage statistics"""
    total_mb: float
    available_mb: float
    used_mb: float
    percent_used: float
    process_mb: float
    python_objects: int

class MemoryManager:
    """Advanced memory management system"""
    
    def __init__(self, monitoring_interval: int = 30):
        """
        Initialize memory manager
        
        Args:
            monitoring_interval: Memory monitoring interval in seconds
        """
        self.monitoring_interval = monitoring_interval
        self._monitoring = False
        self._monitor_thread = None
        self._memory_history = []
        self._cleanup_callbacks = []
        
        logger.info("MemoryManager initialized")
    
    def get_memory_stats(self) -> MemoryStats:
        """Get current memory statistics"""
        try:
            # System memory
            memory = psutil.virtual_memory()
            
            # Process memory
            process = psutil.Process()
            process_memory = process.memory_info()
            
            # Python object count
            python_objects = len(gc.get_objects())
            
            return MemoryStats(
                total_mb=memory.total / (1024 * 1024),
                available_mb=memory.available / (1024 * 1024),
                used_mb=memory.used / (1024 * 1024),
                percent_used=memory.percent,
                process_mb=process_memory.rss / (1024 * 1024),
                python_objects=python_objects
            )
        except Exception as e:
            logger.warning(f"Failed to get memory stats: {e}")
            return MemoryStats(0, 0, 0, 0, 0, 0)
    
    def start_monitoring(self) -> None:
        """Start memory monitoring"""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_memory, daemon=True)
        self._monitor_thread.start()
        logger.info("Memory monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop memory monitoring"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1)
        logger.info("Memory monitoring stopped")
    
    def _monitor_memory(self) -> None:
        """Background memory monitoring"""
        while self._monitoring:
            try:
                stats = self.get_memory_stats()
                self._memory_history.append({
                    'timestamp': time.time(),
                    'stats': stats
                })
                
                # Keep only last 100 entries
                if len(self._memory_history) > 100:
                    self._memory_history = self._memory_history[-100:]
                
                # Check for memory pressure
                if stats.percent_used > 85:
                    logger.warning(f"High memory usage: {stats.percent_used:.1f}%")
                    self._trigger_cleanup()
                
                time.sleep(self.monitoring_interval)
            except Exception as e:
                logger.error(f"Memory monitoring error: {e}")
                time.sleep(self.monitoring_interval)
    
    def _trigger_cleanup(self) -> None:
        """Trigger memory cleanup"""
        logger.info("Triggering memory cleanup")
        
        # Run registered cleanup callbacks
        for callback in self._cleanup_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Cleanup callback failed: {e}")
        
        # Force garbage collection
        self.force_garbage_collection()
    
    def force_garbage_collection(self) -> Dict[str, int]:
        """Force garbage collection and return collection stats"""
        before = self.get_memory_stats()
        
        # Run garbage collection
        collected = gc.collect()
        
        after = self.get_memory_stats()
        
        freed_mb = before.process_mb - after.process_mb
        
        logger.info(f"Garbage collection: {collected} objects collected, "
                   f"{freed_mb:.1f}MB freed")
        
        return {
            'objects_collected': collected,
            'memory_freed_mb': freed_mb,
            'before_mb': before.process_mb,
            'after_mb': after.process_mb
        }
    
    def add_cleanup_callback(self, callback: Callable[[], None]) -> None:
        """Add a cleanup callback"""
        self._cleanup_callbacks.append(callback)
        logger.debug(f"Added cleanup callback: {callback.__name__}")
    
    def remove_cleanup_callback(self, callback: Callable[[], None]) -> None:
        """Remove a cleanup callback"""
        if callback in self._cleanup_callbacks:
            self._cleanup_callbacks.remove(callback)
            logger.debug(f"Removed cleanup callback: {callback.__name__}")
    
    def get_memory_history(self) -> List[Dict[str, Any]]:
        """Get memory usage history"""
        return self._memory_history.copy()
    
    def get_memory_trend(self) -> Dict[str, Any]:
        """Get memory usage trend analysis"""
        if len(self._memory_history) < 2:
            return {'trend': 'insufficient_data'}
        
        recent = self._memory_history[-10:]  # Last 10 measurements
        older = self._memory_history[-20:-10] if len(self._memory_history) >= 20 else []
        
        if not older:
            return {'trend': 'insufficient_data'}
        
        recent_avg = sum(entry['stats'].percent_used for entry in recent) / len(recent)
        older_avg = sum(entry['stats'].percent_used for entry in older) / len(older)
        
        trend = 'stable'
        if recent_avg > older_avg + 5:
            trend = 'increasing'
        elif recent_avg < older_avg - 5:
            trend = 'decreasing'
        
        return {
            'trend': trend,
            'recent_avg': recent_avg,
            'older_avg': older_avg,
            'change': recent_avg - older_avg
        }

@contextmanager
def memory_monitored(operation_name: str = "operation"):
    """Context manager for memory monitoring during operations"""
    manager = get_memory_manager()
    start_stats = manager.get_memory_stats()
    
    logger.debug(f"Starting {operation_name} - Memory: {start_stats.process_mb:.1f}MB")
    
    try:
        yield
    finally:
        end_stats = manager.get_memory_stats()
        memory_delta = end_stats.process_mb - start_stats.process_mb
        
        logger.debug(f"Completed {operation_name} - Memory delta: {memory_delta:+.1f}MB "
                    f"(now: {end_stats.process_mb:.1f}MB)")
        
        # Trigger cleanup if memory usage increased significantly
        if memory_delta > 100:  # More than 100MB increase
            logger.warning(f"Significant memory increase in {operation_name}: {memory_delta:.1f}MB")
            manager.force_garbage_collection()

def memory_efficient(func):
    """Decorator for memory-efficient function execution"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        with memory_monitored(func.__name__):
            result = func(*args, **kwargs)
            
            # Force cleanup after function execution
            manager = get_memory_manager()
            manager.force_garbage_collection()
            
            return result
    return wrapper

class MemoryEfficientList:
    """Memory-efficient list implementation"""
    
    def __init__(self, max_size: int = 1000):
        """
        Initialize memory-efficient list
        
        Args:
            max_size: Maximum number of items to keep in memory
        """
        self.max_size = max_size
        self._items = []
        self._overflow_count = 0
    
    def append(self, item: Any) -> None:
        """Add item to list"""
        if len(self._items) >= self.max_size:
            # Remove oldest item
            self._items.pop(0)
            self._overflow_count += 1
        self._items.append(item)
    
    def extend(self, items: List[Any]) -> None:
        """Add multiple items to list"""
        for item in items:
            self.append(item)
    
    def get_items(self) -> List[Any]:
        """Get all items"""
        return self._items.copy()
    
    def clear(self) -> None:
        """Clear all items"""
        self._items.clear()
        self._overflow_count = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get list statistics"""
        return {
            'current_size': len(self._items),
            'max_size': self.max_size,
            'overflow_count': self._overflow_count,
            'memory_efficient': len(self._items) <= self.max_size
        }

class StreamingProcessor:
    """Memory-efficient streaming processor"""
    
    def __init__(self, chunk_size: int = 1000):
        """
        Initialize streaming processor
        
        Args:
            chunk_size: Size of processing chunks
        """
        self.chunk_size = chunk_size
        self.processed_count = 0
    
    def process_stream(self, items: List[Any], processor_func: Callable) -> List[Any]:
        """
        Process items in streaming fashion
        
        Args:
            items: List of items to process
            processor_func: Function to process each chunk
            
        Returns:
            List of processed results
        """
        results = []
        
        for i in range(0, len(items), self.chunk_size):
            chunk = items[i:i + self.chunk_size]
            
            # Process chunk
            chunk_results = processor_func(chunk)
            results.extend(chunk_results)
            
            # Update progress
            self.processed_count += len(chunk)
            
            # Force cleanup after each chunk
            gc.collect()
            
            logger.debug(f"Processed chunk {i//self.chunk_size + 1}, "
                        f"total processed: {self.processed_count}")
        
        return results

# Global memory manager instance
_memory_manager: Optional[MemoryManager] = None

def get_memory_manager() -> MemoryManager:
    """Get global memory manager instance"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager

def cleanup_memory() -> Dict[str, int]:
    """Cleanup memory and return stats"""
    manager = get_memory_manager()
    return manager.force_garbage_collection()

def start_memory_monitoring() -> None:
    """Start global memory monitoring"""
    manager = get_memory_manager()
    manager.start_monitoring()

def stop_memory_monitoring() -> None:
    """Stop global memory monitoring"""
    manager = get_memory_manager()
    manager.stop_monitoring()

def get_memory_stats() -> MemoryStats:
    """Get current memory statistics"""
    manager = get_memory_manager()
    return manager.get_memory_stats()
