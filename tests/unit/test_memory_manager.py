"""
Unit tests for MemoryManager
"""

import pytest
import gc
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from langflix.core.memory_manager import (
    MemoryManager, MemoryStats, MemoryEfficientList, StreamingProcessor,
    get_memory_manager, cleanup_memory, start_memory_monitoring,
    stop_memory_monitoring, get_memory_stats, memory_monitored, memory_efficient
)

class TestMemoryStats:
    """Test MemoryStats functionality"""
    
    def test_memory_stats_creation(self):
        """Test memory stats creation"""
        stats = MemoryStats(
            total_mb=1000.0,
            available_mb=500.0,
            used_mb=500.0,
            percent_used=50.0,
            process_mb=100.0,
            python_objects=1000
        )
        
        assert stats.total_mb == 1000.0
        assert stats.available_mb == 500.0
        assert stats.used_mb == 500.0
        assert stats.percent_used == 50.0
        assert stats.process_mb == 100.0
        assert stats.python_objects == 1000

class TestMemoryManager:
    """Test MemoryManager functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.memory_manager = MemoryManager(monitoring_interval=1)
    
    def teardown_method(self):
        """Cleanup test environment"""
        self.memory_manager.stop_monitoring()
    
    @patch('psutil.virtual_memory')
    @patch('psutil.Process')
    def test_get_memory_stats(self, mock_process, mock_virtual_memory):
        """Test getting memory statistics"""
        # Mock system memory
        mock_memory = Mock()
        mock_memory.total = 8 * 1024 * 1024 * 1024  # 8GB
        mock_memory.available = 4 * 1024 * 1024 * 1024  # 4GB
        mock_memory.used = 4 * 1024 * 1024 * 1024  # 4GB
        mock_memory.percent = 50.0
        mock_virtual_memory.return_value = mock_memory
        
        # Mock process memory
        mock_process_instance = Mock()
        mock_process_instance.memory_info.return_value = Mock(rss=100 * 1024 * 1024)  # 100MB
        mock_process.return_value = mock_process_instance
        
        stats = self.memory_manager.get_memory_stats()
        
        assert stats.total_mb == 8192.0  # 8GB in MB
        assert stats.available_mb == 4096.0  # 4GB in MB
        assert stats.used_mb == 4096.0  # 4GB in MB
        assert stats.percent_used == 50.0
        assert stats.process_mb == 100.0
        assert stats.python_objects > 0
    
    def test_force_garbage_collection(self):
        """Test forced garbage collection"""
        # Create some objects to collect
        large_list = [i for i in range(10000)]
        del large_list
        
        # Force garbage collection
        stats = self.memory_manager.force_garbage_collection()
        
        assert 'objects_collected' in stats
        assert 'memory_freed_mb' in stats
        assert 'before_mb' in stats
        assert 'after_mb' in stats
        assert stats['objects_collected'] >= 0
        assert stats['memory_freed_mb'] >= 0
    
    def test_cleanup_callbacks(self):
        """Test cleanup callback registration"""
        callback_called = []
        
        def test_callback():
            callback_called.append("called")
        
        # Add callback
        self.memory_manager.add_cleanup_callback(test_callback)
        assert test_callback in self.memory_manager._cleanup_callbacks
        
        # Trigger cleanup
        self.memory_manager._trigger_cleanup()
        assert "called" in callback_called
        
        # Remove callback
        self.memory_manager.remove_cleanup_callback(test_callback)
        assert test_callback not in self.memory_manager._cleanup_callbacks
    
    def test_memory_history(self):
        """Test memory history tracking"""
        # Get initial stats
        initial_stats = self.memory_manager.get_memory_stats()
        
        # Start monitoring briefly
        self.memory_manager.start_monitoring()
        time.sleep(0.1)  # Brief monitoring
        self.memory_manager.stop_monitoring()
        
        # Check history
        history = self.memory_manager.get_memory_history()
        assert len(history) > 0
        assert 'timestamp' in history[0]
        assert 'stats' in history[0]
    
    def test_memory_trend_analysis(self):
        """Test memory trend analysis"""
        # Add some mock history
        now = time.time()
        self.memory_manager._memory_history = [
            {'timestamp': now - 20, 'stats': MemoryStats(0, 0, 0, 20.0, 0, 0)},
            {'timestamp': now - 10, 'stats': MemoryStats(0, 0, 0, 30.0, 0, 0)},
            {'timestamp': now, 'stats': MemoryStats(0, 0, 0, 40.0, 0, 0)}
        ]
        
        trend = self.memory_manager.get_memory_trend()
        
        assert 'trend' in trend
        assert 'recent_avg' in trend
        assert 'older_avg' in trend
        assert 'change' in trend

class TestMemoryEfficientList:
    """Test MemoryEfficientList functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.efficient_list = MemoryEfficientList(max_size=5)
    
    def test_basic_operations(self):
        """Test basic list operations"""
        # Add items
        self.efficient_list.append("item1")
        self.efficient_list.append("item2")
        self.efficient_list.append("item3")
        
        # Get items
        items = self.efficient_list.get_items()
        assert items == ["item1", "item2", "item3"]
        
        # Get stats
        stats = self.efficient_list.get_stats()
        assert stats['current_size'] == 3
        assert stats['max_size'] == 5
        assert stats['overflow_count'] == 0
        assert stats['memory_efficient'] is True
    
    def test_overflow_handling(self):
        """Test overflow handling"""
        # Add more items than max_size
        for i in range(10):
            self.efficient_list.append(f"item_{i}")
        
        # Check that only last 5 items are kept
        items = self.efficient_list.get_items()
        assert len(items) == 5
        assert items == ["item_5", "item_6", "item_7", "item_8", "item_9"]
        
        # Check stats
        stats = self.efficient_list.get_stats()
        assert stats['current_size'] == 5
        assert stats['overflow_count'] == 5
        assert stats['memory_efficient'] is True
    
    def test_extend_operation(self):
        """Test extend operation"""
        # Extend with multiple items
        self.efficient_list.extend(["item1", "item2", "item3"])
        
        items = self.efficient_list.get_items()
        assert items == ["item1", "item2", "item3"]
    
    def test_clear_operation(self):
        """Test clear operation"""
        # Add items
        self.efficient_list.append("item1")
        self.efficient_list.append("item2")
        
        # Clear
        self.efficient_list.clear()
        
        # Check that it's empty
        items = self.efficient_list.get_items()
        assert len(items) == 0
        
        stats = self.efficient_list.get_stats()
        assert stats['current_size'] == 0
        assert stats['overflow_count'] == 0

class TestStreamingProcessor:
    """Test StreamingProcessor functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.processor = StreamingProcessor(chunk_size=3)
    
    def test_process_stream(self):
        """Test streaming processing"""
        def double_item(item):
            return item * 2
        
        items = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        results = self.processor.process_stream(items, double_item)
        
        expected = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20]
        assert results == expected
        assert self.processor.processed_count == 10
    
    def test_process_stream_with_small_chunks(self):
        """Test streaming processing with small chunks"""
        def identity(item):
            return item
        
        items = [1, 2]  # Less than chunk_size
        results = self.processor.process_stream(items, identity)
        
        assert results == [1, 2]
        assert self.processor.processed_count == 2

class TestContextManagers:
    """Test context managers and decorators"""
    
    def test_memory_monitored_context(self):
        """Test memory_monitored context manager"""
        with memory_monitored("test_operation"):
            # Simulate some work
            large_list = [i for i in range(1000)]
            del large_list
    
    def test_memory_efficient_decorator(self):
        """Test memory_efficient decorator"""
        @memory_efficient
        def test_function(x):
            return x * 2
        
        result = test_function(5)
        assert result == 10

class TestGlobalFunctions:
    """Test global functions"""
    
    def test_get_memory_manager(self):
        """Test getting global memory manager"""
        manager = get_memory_manager()
        assert isinstance(manager, MemoryManager)
    
    def test_cleanup_memory(self):
        """Test cleanup_memory function"""
        stats = cleanup_memory()
        assert isinstance(stats, dict)
        assert 'objects_collected' in stats
        assert 'memory_freed_mb' in stats
    
    def test_get_memory_stats(self):
        """Test get_memory_stats function"""
        stats = get_memory_stats()
        assert isinstance(stats, MemoryStats)
        assert stats.total_mb >= 0
        assert stats.available_mb >= 0
        assert stats.used_mb >= 0
        assert stats.percent_used >= 0
        assert stats.process_mb >= 0
        assert stats.python_objects >= 0
    
    def test_memory_monitoring_control(self):
        """Test memory monitoring control functions"""
        # Start monitoring
        start_memory_monitoring()
        
        # Brief wait
        time.sleep(0.1)
        
        # Stop monitoring
        stop_memory_monitoring()

class TestIntegration:
    """Integration tests"""
    
    def test_memory_manager_integration(self):
        """Test memory manager integration"""
        manager = MemoryManager()
        
        # Test basic operations
        stats1 = manager.get_memory_stats()
        assert isinstance(stats1, MemoryStats)
        
        # Test garbage collection
        gc_stats = manager.force_garbage_collection()
        assert isinstance(gc_stats, dict)
        
        # Test cleanup callbacks
        callback_called = []
        
        def test_callback():
            callback_called.append("test")
        
        manager.add_cleanup_callback(test_callback)
        manager._trigger_cleanup()
        assert "test" in callback_called
        
        manager.remove_cleanup_callback(test_callback)
    
    def test_memory_efficient_list_integration(self):
        """Test memory efficient list integration"""
        efficient_list = MemoryEfficientList(max_size=3)
        
        # Test normal operations
        efficient_list.append("a")
        efficient_list.append("b")
        efficient_list.append("c")
        
        items = efficient_list.get_items()
        assert items == ["a", "b", "c"]
        
        # Test overflow
        efficient_list.append("d")
        efficient_list.append("e")
        
        items = efficient_list.get_items()
        assert items == ["c", "d", "e"]
        
        # Test stats
        stats = efficient_list.get_stats()
        assert stats['current_size'] == 3
        assert stats['overflow_count'] == 2
    
    def test_streaming_processor_integration(self):
        """Test streaming processor integration"""
        processor = StreamingProcessor(chunk_size=2)
        
        def process_chunk(chunk):
            return [item * 2 for item in chunk]
        
        items = [1, 2, 3, 4, 5]
        results = processor.process_stream(items, process_chunk)
        
        assert results == [2, 4, 6, 8, 10]
        assert processor.processed_count == 5
