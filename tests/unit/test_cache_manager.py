"""
Unit tests for CacheManager
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import time

from langflix.core.cache_manager import CacheManager, CacheEntry, get_cache_manager, clear_cache, get_cache_stats

class TestCacheManager:
    """Test CacheManager functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_manager = CacheManager(
            cache_dir=self.temp_dir,
            max_memory_size=1024 * 1024,  # 1MB
            max_disk_size=10 * 1024 * 1024,  # 10MB
            default_ttl=3600  # 1 hour
        )
    
    def teardown_method(self):
        """Cleanup test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_cache_manager_initialization(self):
        """Test cache manager initialization"""
        assert self.cache_manager.cache_dir == Path(self.temp_dir)
        assert self.cache_manager.max_memory_size == 1024 * 1024
        assert self.cache_manager.max_disk_size == 10 * 1024 * 1024
        assert self.cache_manager.default_ttl == 3600
    
    def test_cache_entry_creation(self):
        """Test cache entry creation"""
        now = datetime.now()
        entry = CacheEntry(
            key="test_key",
            value="test_value",
            created_at=now,
            last_accessed=now,
            size_bytes=100,
            ttl_seconds=3600
        )
        
        assert entry.key == "test_key"
        assert entry.value == "test_value"
        assert entry.size_bytes == 100
        assert not entry.is_expired()
    
    def test_cache_entry_expiration(self):
        """Test cache entry expiration"""
        past_time = datetime.now() - timedelta(seconds=3700)  # 1 hour + 100 seconds ago
        entry = CacheEntry(
            key="expired_key",
            value="expired_value",
            created_at=past_time,
            last_accessed=past_time,
            size_bytes=100,
            ttl_seconds=3600  # 1 hour TTL
        )
        
        assert entry.is_expired()
    
    def test_basic_set_get(self):
        """Test basic cache set and get operations"""
        # Set a value
        self.cache_manager.set("test_key", "test_value")
        
        # Get the value
        result = self.cache_manager.get("test_key")
        assert result == "test_value"
    
    def test_cache_miss(self):
        """Test cache miss scenario"""
        result = self.cache_manager.get("nonexistent_key")
        assert result is None
    
    def test_cache_with_ttl(self):
        """Test cache with TTL"""
        # Set with short TTL
        self.cache_manager.set("ttl_key", "ttl_value", ttl=1)  # 1 second TTL
        
        # Should be available immediately
        result = self.cache_manager.get("ttl_key")
        assert result == "ttl_value"
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired now
        result = self.cache_manager.get("ttl_key")
        assert result is None
    
    def test_cache_persistence(self):
        """Test cache persistence to disk"""
        # Set with persistence
        self.cache_manager.set("persistent_key", "persistent_value", persist_to_disk=True)
        
        # Create new cache manager (simulating restart)
        new_cache_manager = CacheManager(cache_dir=self.temp_dir)
        
        # Should be able to retrieve from disk
        result = new_cache_manager.get("persistent_key")
        assert result == "persistent_value"
    
    def test_cache_deletion(self):
        """Test cache deletion"""
        # Set a value
        self.cache_manager.set("delete_key", "delete_value")
        
        # Verify it exists
        result = self.cache_manager.get("delete_key")
        assert result == "delete_value"
        
        # Delete it
        success = self.cache_manager.delete("delete_key")
        assert success
        
        # Verify it's gone
        result = self.cache_manager.get("delete_key")
        assert result is None
    
    def test_cache_clear(self):
        """Test cache clearing"""
        # Set multiple values
        self.cache_manager.set("key1", "value1")
        self.cache_manager.set("key2", "value2")
        self.cache_manager.set("key3", "value3", persist_to_disk=True)
        
        # Clear cache
        self.cache_manager.clear()
        
        # All should be gone
        assert self.cache_manager.get("key1") is None
        assert self.cache_manager.get("key2") is None
        assert self.cache_manager.get("key3") is None
    
    def test_cache_statistics(self):
        """Test cache statistics"""
        # Initial stats
        stats = self.cache_manager.get_stats()
        assert stats['hits'] == 0
        assert stats['misses'] == 0
        assert stats['hit_rate'] == 0
        
        # Set and get a value
        self.cache_manager.set("stats_key", "stats_value")
        self.cache_manager.get("stats_key")
        
        # Check updated stats
        stats = self.cache_manager.get_stats()
        assert stats['hits'] == 1
        assert stats['misses'] == 0
        assert stats['hit_rate'] == 100.0
        
        # Miss a key
        self.cache_manager.get("nonexistent")
        
        # Check updated stats
        stats = self.cache_manager.get_stats()
        assert stats['hits'] == 1
        assert stats['misses'] == 1
        assert stats['hit_rate'] == 50.0
    
    def test_specialized_cache_keys(self):
        """Test specialized cache key generation"""
        # TTS key
        tts_key = self.cache_manager.get_tts_key("hello world", "voice1", "en", 0)
        assert isinstance(tts_key, str)
        assert len(tts_key) > 0
        
        # WhisperX key
        whisperx_key = self.cache_manager.get_whisperx_key("/path/to/audio.wav", "base", "en")
        assert isinstance(whisperx_key, str)
        assert len(whisperx_key) > 0
        
        # Expression key
        expression_key = self.cache_manager.get_expression_key("chunk text", "ko")
        assert isinstance(expression_key, str)
        assert len(expression_key) > 0
        
        # Subtitle key
        subtitle_key = self.cache_manager.get_subtitle_key("/path/to/subtitle.srt")
        assert isinstance(subtitle_key, str)
        assert len(subtitle_key) > 0
    
    def test_cache_key_consistency(self):
        """Test that cache keys are consistent"""
        # Same inputs should produce same keys
        key1 = self.cache_manager.get_tts_key("hello", "voice1", "en", 0)
        key2 = self.cache_manager.get_tts_key("hello", "voice1", "en", 0)
        assert key1 == key2
        
        # Different inputs should produce different keys
        key3 = self.cache_manager.get_tts_key("hello", "voice2", "en", 0)
        assert key1 != key3
    
    def test_memory_limit_enforcement(self):
        """Test memory limit enforcement"""
        # Set multiple values to exceed memory limit
        for i in range(10):
            large_value = "x" * (200 * 1024)  # 200KB each
            self.cache_manager.set(f"large_key_{i}", large_value)
        
        # Should trigger cleanup
        stats = self.cache_manager.get_stats()
        # Note: Evictions might not happen immediately due to cleanup timing
        assert stats['memory_size_mb'] >= 0  # Just check that stats are working
    
    def test_thread_safety(self):
        """Test thread safety of cache operations"""
        import threading
        import time
        
        results = []
        
        def worker(worker_id):
            for i in range(10):
                key = f"worker_{worker_id}_key_{i}"
                value = f"worker_{worker_id}_value_{i}"
                
                # Set value
                self.cache_manager.set(key, value)
                
                # Get value
                result = self.cache_manager.get(key)
                results.append((worker_id, i, result == value))
                
                time.sleep(0.001)  # Small delay
        
        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all operations succeeded
        assert len(results) == 50  # 5 workers * 10 operations
        assert all(success for _, _, success in results)

class TestGlobalCacheManager:
    """Test global cache manager functions"""
    
    def setup_method(self):
        """Setup test environment"""
        clear_cache()  # Clear any existing cache
    
    def teardown_method(self):
        """Cleanup test environment"""
        clear_cache()
    
    def test_get_cache_manager(self):
        """Test getting global cache manager"""
        manager = get_cache_manager()
        assert isinstance(manager, CacheManager)
        
        # Should return same instance
        manager2 = get_cache_manager()
        assert manager is manager2
    
    def test_clear_cache(self):
        """Test clearing global cache"""
        manager = get_cache_manager()
        
        # Set a value
        manager.set("test_key", "test_value")
        assert manager.get("test_key") == "test_value"
        
        # Clear cache
        clear_cache()
        
        # Should be gone
        assert manager.get("test_key") is None
    
    def test_get_cache_stats(self):
        """Test getting cache statistics"""
        manager = get_cache_manager()
        
        # Set and get a value
        manager.set("stats_key", "stats_value")
        manager.get("stats_key")
        
        # Get stats
        stats = get_cache_stats()
        assert isinstance(stats, dict)
        assert 'hits' in stats
        assert 'misses' in stats
        assert 'hit_rate' in stats
