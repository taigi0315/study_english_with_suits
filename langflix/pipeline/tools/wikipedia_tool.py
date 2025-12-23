"""
Wikipedia Tool for Show Bible Creation
Uses Wikipedia API to gather show premise and character information
"""
import logging
import time
from typing import Optional, Tuple
import wikipedia

logger = logging.getLogger(__name__)


class WikipediaTool:
    """Tool for querying Wikipedia to gather show context"""

    def __init__(self, max_retries: int = 3, retry_delay: float = 2.0):
        """
        Initialize Wikipedia tool

        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries (exponential backoff)
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Set Wikipedia language (can be parameterized later)
        wikipedia.set_lang("en")

    def search_show_premise(self, show_name: str) -> Optional[str]:
        """
        Search Wikipedia for show premise/plot summary

        Args:
            show_name: Name of the TV show or movie

        Returns:
            Wikipedia summary text or None if not found
        """
        query = f"{show_name} TV series plot summary premise"
        logger.info(f"Searching Wikipedia for premise: {query}")

        return self._search_with_retry(query, section="premise")

    def search_show_characters(self, show_name: str) -> Optional[str]:
        """
        Search Wikipedia for show characters and relationships

        Args:
            show_name: Name of the TV show or movie

        Returns:
            Wikipedia character information or None if not found
        """
        query = f"{show_name} TV series main characters descriptions relationships"
        logger.info(f"Searching Wikipedia for characters: {query}")

        return self._search_with_retry(query, section="characters")

    def _search_with_retry(self, query: str, section: str) -> Optional[str]:
        """
        Execute Wikipedia search with exponential backoff retry

        Args:
            query: Search query
            section: Section identifier for logging

        Returns:
            Wikipedia content or None
        """
        for attempt in range(self.max_retries):
            try:
                # Search for the page
                search_results = wikipedia.search(query, results=3)

                if not search_results:
                    logger.warning(f"No Wikipedia results found for: {query}")
                    return None

                # Try to get the first result's summary
                page_title = search_results[0]
                logger.info(f"Found Wikipedia page: {page_title}")

                # Get full page content (not just summary)
                page = wikipedia.page(page_title, auto_suggest=False)

                # Return full content (can be refined to specific sections later)
                content = page.content

                logger.info(f"✅ Successfully retrieved {section} from Wikipedia ({len(content)} chars)")
                return content

            except wikipedia.exceptions.DisambiguationError as e:
                # Multiple possible pages - try the first option
                logger.warning(f"Disambiguation error for '{query}', trying first option: {e.options[0]}")
                try:
                    page = wikipedia.page(e.options[0], auto_suggest=False)
                    content = page.content
                    logger.info(f"✅ Retrieved {section} from disambiguation ({len(content)} chars)")
                    return content
                except Exception as inner_e:
                    logger.error(f"Failed to retrieve disambiguation option: {inner_e}")

            except wikipedia.exceptions.PageError:
                logger.error(f"Wikipedia page not found for: {query}")
                return None

            except Exception as e:
                # Network or other errors - retry with backoff
                wait_time = self.retry_delay * (2 ** attempt)
                logger.warning(
                    f"Wikipedia API error on attempt {attempt + 1}/{self.max_retries}: {e}. "
                    f"Retrying in {wait_time}s..."
                )

                if attempt < self.max_retries - 1:
                    time.sleep(wait_time)
                else:
                    logger.error(f"Wikipedia API failed after {self.max_retries} attempts")
                    return None

        return None

    def create_show_bible(self, show_name: str) -> Tuple[bool, Optional[str]]:
        """
        Create a complete Show Bible by combining premise and character info

        Args:
            show_name: Name of the TV show or movie

        Returns:
            Tuple of (success: bool, bible_content: Optional[str])
        """
        logger.info(f"📖 Creating Show Bible for: {show_name}")

        # Get premise
        premise = self.search_show_premise(show_name)
        if not premise:
            logger.error(f"❌ Failed to retrieve premise for: {show_name}")
            return False, None

        # Get characters
        characters = self.search_show_characters(show_name)
        if not characters:
            logger.warning(f"⚠️ Failed to retrieve characters for: {show_name}, using premise only")
            characters = "(Character information not available)"

        # Format as Show Bible
        bible_content = f"""=== SHOW BIBLE: {show_name} ===

[PREMISE]
{premise}

[CHARACTERS & RELATIONSHIPS]
{characters}

---
Generated by LangFlix Wikipedia Tool
"""

        logger.info(f"✅ Show Bible created successfully ({len(bible_content)} chars)")
        return True, bible_content
