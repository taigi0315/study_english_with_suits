"""
LLM Test Cache - Development utility for caching and reusing LLM responses.

This module provides development-time caching to skip LLM API calls during
rapid iteration. When test_llm mode is enabled, it will:
1. Load a previously cached LLM response (if available)
2. Save new LLM responses for future reuse

Usage:
    - First run: Response gets saved to cache
    - Subsequent runs with test_llm=True: Load from cache, skip API call
"""

import json
import logging
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Default cache directory under assets
DEFAULT_CACHE_DIR = Path("assets/cache/llm_test_cache")


class LLMTestCache:
    """
    Development LLM cache for fast iteration.
    
    Unlike the production cache (cache_manager), this cache:
    - Uses human-readable filenames
    - Persists across restarts
    - Is explicitly controlled by test_llm flag
    """
    
    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def _get_cache_path(self, cache_type: str, identifier: str = "default") -> Path:
        """
        Get path to cache file.
        
        Args:
            cache_type: Type of cache (e.g., "expression_analysis", "content_selection")
            identifier: Optional identifier to distinguish different caches
            
        Returns:
            Path to cache file
        """
        # Use identifier in filename, sanitize for filesystem
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in identifier)[:50]
        return self.cache_dir / f"{cache_type}_{safe_id}.json"
    
    def save_response(
        self, 
        cache_type: str, 
        response_data: Any,
        identifier: str = "default",
        metadata: Dict[str, Any] = None
    ) -> Path:
        """
        Save LLM response to cache file.
        
        Args:
            cache_type: Type of cache (e.g., "expression_analysis")
            response_data: The LLM response data to cache (dict or list)
            identifier: Optional identifier (e.g., show name, episode)
            metadata: Optional metadata to store with the cache
            
        Returns:
            Path to saved cache file
        """
        cache_path = self._get_cache_path(cache_type, identifier)
        
        cache_entry = {
            "timestamp": datetime.now().isoformat(),
            "cache_type": cache_type,
            "identifier": identifier,
            "metadata": metadata or {},
            "data": response_data
        }
        
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_entry, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"💾 Saved LLM response to test cache: {cache_path}")
        return cache_path
    
    def load_response(
        self, 
        cache_type: str, 
        identifier: str = "default"
    ) -> Optional[Any]:
        """
        Load cached LLM response.
        
        Args:
            cache_type: Type of cache to load
            identifier: Identifier used when saving
            
        Returns:
            Cached response data, or None if not found
        """
        cache_path = self._get_cache_path(cache_type, identifier)
        
        if not cache_path.exists():
            logger.debug(f"No test cache found at: {cache_path}")
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_entry = json.load(f)
            
            # Log cache info
            timestamp = cache_entry.get("timestamp", "unknown")
            logger.info(f"📂 Loaded LLM response from test cache (saved: {timestamp})")
            
            return cache_entry.get("data")
            
        except Exception as e:
            logger.warning(f"Failed to load test cache: {e}")
            return None
    
    def has_cache(self, cache_type: str, identifier: str = "default") -> bool:
        """Check if cache exists for given type and identifier."""
        cache_path = self._get_cache_path(cache_type, identifier)
        return cache_path.exists()
    
    def clear_cache(self, cache_type: str = None, identifier: str = None) -> int:
        """
        Clear cache files.
        
        Args:
            cache_type: If provided, clear only this type
            identifier: If provided, clear only this identifier
            
        Returns:
            Number of files deleted
        """
        deleted = 0
        
        for cache_file in self.cache_dir.glob("*.json"):
            should_delete = True
            
            if cache_type:
                should_delete = cache_file.name.startswith(cache_type)
            if identifier and should_delete:
                should_delete = identifier in cache_file.name
                
            if should_delete:
                cache_file.unlink()
                deleted += 1
                logger.info(f"🗑️ Deleted cache file: {cache_file}")
        
        return deleted
    
    def list_caches(self) -> List[Dict[str, Any]]:
        """List all available cache files with their metadata."""
        caches = []
        
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_entry = json.load(f)
                    
                caches.append({
                    "file": str(cache_file),
                    "cache_type": cache_entry.get("cache_type"),
                    "identifier": cache_entry.get("identifier"),
                    "timestamp": cache_entry.get("timestamp"),
                    "metadata": cache_entry.get("metadata", {})
                })
            except Exception as e:
                caches.append({
                    "file": str(cache_file),
                    "error": str(e)
                })
        
        return caches


# Global instance
_test_cache: Optional[LLMTestCache] = None


def get_test_cache() -> LLMTestCache:
    """Get the global test cache instance."""
    global _test_cache
    if _test_cache is None:
        _test_cache = LLMTestCache()
    return _test_cache


def save_llm_test_response(
    cache_type: str,
    response_data: Any,
    identifier: str = "default",
    metadata: Dict[str, Any] = None
) -> Path:
    """Convenience function to save LLM response to test cache."""
    return get_test_cache().save_response(cache_type, response_data, identifier, metadata)


def load_llm_test_response(
    cache_type: str,
    identifier: str = "default"
) -> Optional[Any]:
    """Convenience function to load LLM response from test cache."""
    return get_test_cache().load_response(cache_type, identifier)


def has_llm_test_cache(
    cache_type: str,
    identifier: str = "default"
) -> bool:
    """Convenience function to check if test cache exists."""
    return get_test_cache().has_cache(cache_type, identifier)
