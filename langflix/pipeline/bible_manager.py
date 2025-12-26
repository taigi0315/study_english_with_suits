"""
Show Bible Manager
Handles caching and retrieval of Show Bibles
"""
import logging
import os
from pathlib import Path
from typing import Optional, List
from langflix.pipeline.tools.wikipedia_tool import WikipediaTool

logger = logging.getLogger(__name__)


class ShowBibleManager:
    """Manages Show Bible creation, caching, and retrieval"""

    def __init__(self, cache_dir: str = "langflix/pipeline/artifacts/show_bibles"):
        """
        Initialize Show Bible Manager

        Args:
            cache_dir: Directory to store cached Show Bibles
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.wikipedia_tool = WikipediaTool()

        logger.info(f"ShowBibleManager initialized with cache_dir: {self.cache_dir}")

    def _get_bible_path(self, show_name: str) -> Path:
        """
        Get the file path for a show's bible

        Args:
            show_name: Name of the show

        Returns:
            Path to the bible file
        """
        # Sanitize show name for filename
        safe_name = show_name.replace(" ", "_").replace("/", "_")
        return self.cache_dir / f"{safe_name}_bible.txt"

    def get_or_create_bible(self, show_name: str, force_refresh: bool = False) -> Optional[str]:
        """
        Get Show Bible from cache or create new one

        Args:
            show_name: Name of the show
            force_refresh: If True, regenerate even if cached

        Returns:
            Show Bible content or None if failed
        """
        bible_path = self._get_bible_path(show_name)

        # Check cache first (unless force refresh)
        if not force_refresh and bible_path.exists():
            logger.info(f"📖 Loading cached Show Bible for: {show_name}")
            try:
                with open(bible_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                logger.info(f"✅ Loaded cached bible ({len(content)} chars)")
                return content
            except Exception as e:
                logger.error(f"Failed to load cached bible: {e}")
                # Fall through to regenerate

        # Create new bible
        logger.info(f"📝 Creating new Show Bible for: {show_name}")
        success, content = self.wikipedia_tool.create_show_bible(show_name)

        if not success or not content:
            logger.error(f"❌ Failed to create Show Bible for: {show_name}")
            return None

        # Cache the bible
        try:
            with open(bible_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"💾 Cached Show Bible to: {bible_path}")
        except Exception as e:
            logger.warning(f"Failed to cache bible (non-fatal): {e}")

        return content

    def list_cached_bibles(self) -> List[str]:
        """
        List all cached Show Bibles

        Returns:
            List of show names with cached bibles
        """
        if not self.cache_dir.exists():
            return []

        bibles = []
        for bible_file in self.cache_dir.glob("*_bible.txt"):
            # Extract show name from filename
            show_name = bible_file.stem.replace("_bible", "").replace("_", " ")
            bibles.append(show_name)

        return sorted(bibles)

    def delete_bible(self, show_name: str) -> bool:
        """
        Delete a cached Show Bible

        Args:
            show_name: Name of the show

        Returns:
            True if deleted successfully
        """
        bible_path = self._get_bible_path(show_name)

        if not bible_path.exists():
            logger.warning(f"Bible not found for deletion: {show_name}")
            return False

        try:
            os.remove(bible_path)
            logger.info(f"🗑️ Deleted bible for: {show_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete bible: {e}")
            return False

    def get_bible_stats(self, show_name: str) -> Optional[dict]:
        """
        Get statistics about a cached bible

        Args:
            show_name: Name of the show

        Returns:
            Dict with stats or None
        """
        bible_path = self._get_bible_path(show_name)

        if not bible_path.exists():
            return None

        try:
            stats = bible_path.stat()
            with open(bible_path, 'r', encoding='utf-8') as f:
                content = f.read()

            return {
                "show_name": show_name,
                "file_path": str(bible_path),
                "size_bytes": stats.st_size,
                "size_kb": round(stats.st_size / 1024, 2),
                "created_time": stats.st_ctime,
                "modified_time": stats.st_mtime,
                "char_count": len(content),
                "line_count": content.count('\n')
            }
        except Exception as e:
            logger.error(f"Failed to get bible stats: {e}")
            return None
