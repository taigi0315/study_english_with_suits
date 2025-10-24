"""
Advanced caching system for LangFlix Expression-Based Learning Feature.

This module provides intelligent caching for:
- TTS audio generation
- WhisperX model loading and transcription results
- Expression analysis results
- Subtitle parsing results
- Media metadata

Features:
- Multi-level caching (memory + disk)
- Intelligent cache invalidation
- Cache statistics and monitoring
- Thread-safe operations
- Configurable cache policies
"""

import os
import json
import hashlib
import pickle
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional, Union, List, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Represents a cache entry with metadata"""
    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    size_bytes: int = 0
    ttl_seconds: Optional[int] = None
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        if self.ttl_seconds is None:
            return False
        return datetime.now() > (self.created_at + timedelta(seconds=self.ttl_seconds))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'key': self.key,
            'created_at': self.created_at.isoformat(),
            'last_accessed': self.last_accessed.isoformat(),
            'access_count': self.access_count,
            'size_bytes': self.size_bytes,
            'ttl_seconds': self.ttl_seconds
        }

class CacheManager:
    """Advanced cache manager with intelligent policies"""
    
    def __init__(
        self,
        cache_dir: str = "./cache",
        max_memory_size: int = 100 * 1024 * 1024,  # 100MB
        max_disk_size: int = 1024 * 1024 * 1024,   # 1GB
        default_ttl: Optional[int] = None,
        cleanup_interval: int = 300  # 5 minutes
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_memory_size = max_memory_size
        self.max_disk_size = max_disk_size
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval
        
        # Thread-safe storage
        self._memory_cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        
        # Statistics
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'disk_writes': 0,
            'disk_reads': 0
        }
        
        # Start cleanup thread
        self._cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self._cleanup_thread.start()
        
        logger.info(f"CacheManager initialized: memory={max_memory_size//1024//1024}MB, disk={max_disk_size//1024//1024}MB")
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate a cache key from arguments"""
        # Create a deterministic string from arguments
        key_data = {
            'prefix': prefix,
            'args': args,
            'kwargs': sorted(kwargs.items()) if kwargs else {}
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _get_entry_size(self, value: Any) -> int:
        """Estimate the size of a cache entry"""
        try:
            if isinstance(value, (str, bytes)):
                return len(value)
            elif isinstance(value, (list, tuple)):
                return sum(self._get_entry_size(item) for item in value)
            elif isinstance(value, dict):
                return sum(self._get_entry_size(v) for v in value.values())
            else:
                # For complex objects, use pickle size estimation
                return len(pickle.dumps(value))
        except Exception:
            return 1024  # Default estimate
    
    def _cleanup_worker(self):
        """Background cleanup worker"""
        while True:
            try:
                time.sleep(self.cleanup_interval)
                self._cleanup_expired()
                self._cleanup_oversized()
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
    
    def _cleanup_expired(self):
        """Remove expired entries"""
        with self._lock:
            expired_keys = [
                key for key, entry in self._memory_cache.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                del self._memory_cache[key]
                logger.debug(f"Removed expired cache entry: {key}")
    
    def _cleanup_oversized(self):
        """Remove entries when cache is oversized"""
        with self._lock:
            current_size = sum(entry.size_bytes for entry in self._memory_cache.values())
            
            if current_size > self.max_memory_size:
                # Sort by last accessed time (LRU)
                sorted_entries = sorted(
                    self._memory_cache.items(),
                    key=lambda x: x[1].last_accessed
                )
                
                # Remove oldest entries until under limit
                for key, entry in sorted_entries:
                    if current_size <= self.max_memory_size * 0.8:  # Leave some headroom
                        break
                    
                    del self._memory_cache[key]
                    current_size -= entry.size_bytes
                    self._stats['evictions'] += 1
                    logger.debug(f"Evicted cache entry: {key}")
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self._lock:
            if key in self._memory_cache:
                entry = self._memory_cache[key]
                
                if entry.is_expired():
                    del self._memory_cache[key]
                    self._stats['misses'] += 1
                    return None
                
                # Update access statistics
                entry.last_accessed = datetime.now()
                entry.access_count += 1
                self._stats['hits'] += 1
                
                logger.debug(f"Cache hit: {key}")
                return entry.value
            
            # Try disk cache
            disk_value = self._get_from_disk(key)
            if disk_value is not None:
                self._stats['hits'] += 1
                self._stats['disk_reads'] += 1
                logger.debug(f"Disk cache hit: {key}")
                return disk_value
            
            self._stats['misses'] += 1
            logger.debug(f"Cache miss: {key}")
            return None
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        persist_to_disk: bool = False
    ) -> None:
        """Set value in cache"""
        ttl = ttl or self.default_ttl
        size_bytes = self._get_entry_size(value)
        
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            size_bytes=size_bytes,
            ttl_seconds=ttl
        )
        
        with self._lock:
            self._memory_cache[key] = entry
            
            # Persist to disk if requested
            if persist_to_disk:
                self._save_to_disk(key, value, entry)
        
        logger.debug(f"Cached: {key} (size: {size_bytes} bytes)")
    
    def _get_from_disk(self, key: str) -> Optional[Any]:
        """Get value from disk cache"""
        try:
            cache_file = self.cache_dir / f"{key}.cache"
            if not cache_file.exists():
                return None
            
            with open(cache_file, 'rb') as f:
                data = pickle.load(f)
            
            # Check if expired
            if data.get('ttl_seconds'):
                created_at = datetime.fromisoformat(data['created_at'])
                if datetime.now() > (created_at + timedelta(seconds=data['ttl_seconds'])):
                    cache_file.unlink()  # Remove expired file
                    return None
            
            return data['value']
        except Exception as e:
            logger.warning(f"Failed to read disk cache {key}: {e}")
            return None
    
    def _save_to_disk(self, key: str, value: Any, entry: CacheEntry) -> None:
        """Save value to disk cache"""
        try:
            cache_file = self.cache_dir / f"{key}.cache"
            data = {
                'value': value,
                'created_at': entry.created_at.isoformat(),
                'ttl_seconds': entry.ttl_seconds
            }
            
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)
            
            self._stats['disk_writes'] += 1
            logger.debug(f"Saved to disk cache: {key}")
        except Exception as e:
            logger.warning(f"Failed to save disk cache {key}: {e}")
    
    def delete(self, key: str) -> bool:
        """Delete cache entry"""
        with self._lock:
            # Remove from memory
            if key in self._memory_cache:
                del self._memory_cache[key]
            
            # Remove from disk
            cache_file = self.cache_dir / f"{key}.cache"
            if cache_file.exists():
                cache_file.unlink()
            
            logger.debug(f"Deleted cache entry: {key}")
            return True
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self._memory_cache.clear()
            
            # Clear disk cache
            for cache_file in self.cache_dir.glob("*.cache"):
                cache_file.unlink()
            
            logger.info("Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0
            
            current_memory_size = sum(entry.size_bytes for entry in self._memory_cache.values())
            
            return {
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'hit_rate': round(hit_rate, 2),
                'evictions': self._stats['evictions'],
                'disk_writes': self._stats['disk_writes'],
                'disk_reads': self._stats['disk_reads'],
                'memory_entries': len(self._memory_cache),
                'memory_size_bytes': current_memory_size,
                'memory_size_mb': round(current_memory_size / 1024 / 1024, 2)
            }
    
    def get_tts_key(self, text: str, voice: str, language: str, index: int = 0) -> str:
        """Generate cache key for TTS audio"""
        return self._generate_key("tts", text, voice, language, index)
    
    # Note: get_whisperx_key method removed - using external transcription
    
    def get_expression_key(self, chunk_text: str, language: str) -> str:
        """Generate cache key for expression analysis"""
        return self._generate_key("expression", chunk_text, language)
    
    def get_subtitle_key(self, file_path: str) -> str:
        """Generate cache key for subtitle parsing"""
        return self._generate_key("subtitle", file_path)

# Global cache manager instance
_cache_manager: Optional[CacheManager] = None

def get_cache_manager() -> CacheManager:
    """Get global cache manager instance"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager

def clear_cache() -> None:
    """Clear global cache"""
    global _cache_manager
    if _cache_manager:
        _cache_manager.clear()

def get_cache_stats() -> Dict[str, Any]:
    """Get global cache statistics"""
    global _cache_manager
    if _cache_manager:
        return _cache_manager.get_stats()
    return {}
