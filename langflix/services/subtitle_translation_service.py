"""
Subtitle Translation Service

Translates entire subtitle files from one language to another using batch processing.
Ensures all required subtitle files exist before the main pipeline runs.
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Callable
from dotenv import load_dotenv

import google.generativeai as genai

from langflix.core.dual_subtitle import SubtitleEntry
from langflix.core.subtitle_parser import parse_srt_file
from langflix.core.subtitle_writer import write_srt_file
from langflix.utils.path_utils import discover_subtitle_languages, get_subtitle_file
from langflix.core.error_handler import (
    handle_error_decorator,
    ErrorContext
)
from langflix import settings

# Load environment variables
load_dotenv()

# Get logger
logger = logging.getLogger(__name__)

# Configure Gemini API
genai.configure(
    api_key=os.getenv("GEMINI_API_KEY"),
    client_options={
        "api_endpoint": "generativelanguage.googleapis.com",
    }
)


class SubtitleTranslationService:
    """Service for translating subtitle files using Gemini API."""

    def __init__(self, batch_size: int = 75):
        """
        Initialize the subtitle translation service.

        Args:
            batch_size: Number of subtitle entries to translate per API call (default: 75)
        """
        self.batch_size = batch_size
        self.model_name = settings.get_llm_model_name()
        self.generation_config = settings.get_generation_config()
        logger.info(f"Initialized SubtitleTranslationService with batch_size={batch_size}")

    def ensure_subtitles_exist(
        self,
        subtitle_folder: Path,
        source_language: str,
        required_languages: List[str],
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Dict[str, bool]:
        """
        Ensure all required subtitle files exist, translating if necessary.

        Args:
            subtitle_folder: Path to Netflix subtitle folder
            source_language: Source language name (e.g., "English")
            required_languages: List of required language names (e.g., ["English", "Korean"])
            progress_callback: Optional callback(progress_percent, message)

        Returns:
            Dictionary mapping language to success status

        Raises:
            ValueError: If no subtitle files exist at all
        """
        subtitle_folder = Path(subtitle_folder)

        # Discover existing subtitles
        if progress_callback:
            progress_callback(0, "Discovering existing subtitles...")

        # For discovering subtitles, we need to pass a media file path
        # Since we have the subtitle folder, we need to find the media file
        media_files = []
        folder_name = subtitle_folder.name
        
        # Handle both new and legacy folder structures:
        # NEW: media_folder/Subs/{media_name}/ → parent.parent is media folder
        # LEGACY: media_folder/{media_name}/ → parent is media folder
        if subtitle_folder.parent.name == "Subs":
            # New structure: Subs/{media_name}/ - media is in grandparent
            search_folder = subtitle_folder.parent.parent
        else:
            # Legacy structure: {media_name}/ - media is in parent
            search_folder = subtitle_folder.parent

        # Look for media files with the same base name
        for ext in ['.mp4', '.mkv', '.avi', '.mov']:
            media_file = search_folder / f"{folder_name}{ext}"
            if media_file.exists():
                media_files.append(media_file)
                break

        # If we can't find the media file, use the subtitle folder directly
        media_path = str(media_files[0]) if media_files else str(subtitle_folder)

        available_languages = discover_subtitle_languages(media_path)

        if not available_languages:
            raise ValueError(
                f"No subtitle files found in {subtitle_folder}. "
                f"At least one subtitle file is required for translation."
            )

        logger.info(f"Found existing subtitles for: {list(available_languages.keys())}")
        logger.info(f"Required languages: {required_languages}")

        # Identify missing subtitles
        missing_languages = [lang for lang in required_languages if lang not in available_languages]

        if not missing_languages:
            logger.info("All required subtitles already exist")
            return {lang: True for lang in required_languages}

        logger.info(f"Missing subtitles for: {missing_languages}")

        # Select base subtitle for translation
        base_language, base_subtitle_path = self._smart_select_base_subtitle(
            available_languages, source_language, required_languages
        )

        logger.info(f"Using '{base_language}' subtitle as translation base: {base_subtitle_path}")

        # Load base subtitle entries
        base_entries = self._load_subtitle_entries(base_subtitle_path)
        logger.info(f"Loaded {len(base_entries)} subtitle entries from {base_language}")

        # Translate to each missing language
        results = {lang: True for lang in required_languages if lang in available_languages}

        total_translations = len(missing_languages)
        for idx, target_language in enumerate(missing_languages):
            try:
                if progress_callback:
                    percent = int((idx / total_translations) * 90) + 5
                    progress_callback(percent, f"Translating to {target_language}...")

                # Write translated subtitle file
                output_path = subtitle_folder / f"{target_language}.srt"
                
                # Translate subtitles (with incremental saving)
                translated_entries = self.batch_translate_subtitles(
                    base_entries,
                    base_language,
                    target_language,
                    output_path=str(output_path),
                    progress_callback=lambda p, m: progress_callback(
                        int((idx / total_translations) * 90) + 5 + int(p * 0.9 / total_translations),
                        f"[{target_language}] {m}"
                    ) if progress_callback else None
                )

                # Final write to ensure completeness (though incremental writes happen too)
                write_srt_file(translated_entries, str(output_path))

                logger.info(f"Successfully created {target_language} subtitle: {output_path}")
                results[target_language] = True

            except Exception as e:
                logger.error(f"Failed to translate subtitle to {target_language}: {e}")
                results[target_language] = False

        if progress_callback:
            progress_callback(100, "Subtitle translation complete")

        return results

    def _smart_select_base_subtitle(
        self,
        available: Dict[str, List[str]],
        source_lang: str,
        target_langs: List[str]
    ) -> Tuple[str, str]:
        """
        Select best subtitle file to use as translation base.

        Priority:
        1. Source language (preferred)
        2. Any target language (good fallback)
        3. Any available language (last resort)

        Args:
            available: Dictionary of available languages and their file paths
            source_lang: Preferred source language
            target_langs: List of target languages

        Returns:
            Tuple of (selected_language, file_path)
        """
        # Try source language first
        if source_lang in available:
            return source_lang, available[source_lang][0]

        # Try target languages
        for target in target_langs:
            if target in available:
                logger.warning(f"Source '{source_lang}' not found, using '{target}' as base")
                return target, available[target][0]

        # Last resort: use first available
        first_lang = list(available.keys())[0]
        logger.warning(f"Neither source nor targets found, using '{first_lang}' as base")
        return first_lang, available[first_lang][0]

    def _load_subtitle_entries(self, subtitle_path: str) -> List[SubtitleEntry]:
        """
        Load subtitle file into SubtitleEntry objects.

        Args:
            subtitle_path: Path to SRT file

        Returns:
            List of SubtitleEntry objects
        """
        parsed = parse_srt_file(subtitle_path)
        entries = []

        for i, item in enumerate(parsed, start=1):
            entry = SubtitleEntry(
                index=i,
                start_time=item['start_time'],
                end_time=item['end_time'],
                text=item['text']
            )
            entries.append(entry)

        return entries

    @handle_error_decorator(
        ErrorContext(
            operation="batch_translate_subtitles",
            component="subtitle_translation_service"
        ),
        retry=True,
        fallback=False
    )
    def batch_translate_subtitles(
        self,
        entries: List[SubtitleEntry],
        source_lang: str,
        target_lang: str,
        output_path: Optional[str] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> List[SubtitleEntry]:
        """
        Translate subtitle entries in batches.

        Args:
            entries: List of SubtitleEntry objects to translate
            source_lang: Source language name (e.g., "English")
            target_lang: Target language name (e.g., "Korean")
            output_path: Optional path to save progress incrementally
            progress_callback: Optional callback for progress updates

        Returns:
            List of translated SubtitleEntry objects with same timing

        Raises:
            ValueError: If translation fails or produces invalid results
        """
        logger.info(f"Translating {len(entries)} subtitles from {source_lang} to {target_lang}")

        # Create batches
        batches = [entries[i:i + self.batch_size] for i in range(0, len(entries), self.batch_size)]
        logger.info(f"Created {len(batches)} batches (batch_size={self.batch_size})")

        all_translated = []

        for batch_idx, batch in enumerate(batches):
            try:
                if progress_callback:
                    percent = int((batch_idx / len(batches)) * 100)
                    progress_callback(percent, f"Translating batch {batch_idx + 1}/{len(batches)}...")

                translated_batch = self._translate_batch(batch, source_lang, target_lang)
                all_translated.extend(translated_batch)

                # Incrementally save progress if output path is provided
                if output_path:
                    try:
                        write_srt_file(all_translated, output_path)
                        logger.debug(f"Saved incremental progress to {output_path}")
                    except Exception as save_err:
                        logger.warning(f"Failed to save incremental progress: {save_err}")

                logger.info(f"Successfully translated batch {batch_idx + 1}/{len(batches)}")

            except Exception as e:
                logger.error(f"Failed to translate batch {batch_idx + 1}/{len(batches)}: {e}")
                # Continue with next batch instead of failing entire operation
                continue

        # Check success rate
        success_rate = len(all_translated) / len(entries)
        if success_rate < 0.8:
            raise ValueError(
                f"Translation failed: only {success_rate:.0%} of subtitles translated "
                f"({len(all_translated)}/{len(entries)})"
            )

        logger.info(f"Translation complete: {len(all_translated)}/{len(entries)} subtitles ({success_rate:.0%})")
        return all_translated

    def _translate_batch(
        self,
        batch: List[SubtitleEntry],
        source_lang: str,
        target_lang: str
    ) -> List[SubtitleEntry]:
        """
        Translate a single batch of subtitles.

        Args:
            batch: List of SubtitleEntry objects to translate
            source_lang: Source language name
            target_lang: Target language name

        Returns:
            List of translated SubtitleEntry objects
        """
        # Create prompt
        prompt = self._create_batch_translation_prompt(batch, source_lang, target_lang)

        # Configure model
        model = genai.GenerativeModel(model_name=self.model_name)

        # Generate translation
        logger.debug(f"Sending batch translation request to Gemini API ({len(batch)} entries)")

        if self.generation_config:
            config_obj = genai.types.GenerationConfig(**self.generation_config)
            response = model.generate_content(prompt, generation_config=config_obj)
        else:
            response = model.generate_content(prompt)

        # Extract response text
        response_text = ""
        if hasattr(response, 'text') and response.text:
            response_text = response.text
        elif hasattr(response, 'candidates') and response.candidates:
            if response.candidates[0].content.parts:
                response_text = response.candidates[0].content.parts[0].text

        if not response_text:
            raise ValueError("Empty response from translation API")

        # Parse translation response
        translated_entries = self._parse_batch_translation_response(response_text, batch)

        return translated_entries

    def _create_batch_translation_prompt(
        self,
        batch: List[SubtitleEntry],
        source_lang: str,
        target_lang: str
    ) -> str:
        """
        Create translation prompt for a batch of subtitles.

        Args:
            batch: List of SubtitleEntry objects
            source_lang: Source language name
            target_lang: Target language name

        Returns:
            Formatted prompt string
        """
        # Load template
        template_path = Path(__file__).parent.parent / "templates" / "subtitle_batch_translation_prompt.txt"

        if template_path.exists():
            template = template_path.read_text(encoding='utf-8')
        else:
            logger.warning(f"Template not found at {template_path}, using default")
            template = self._get_default_batch_translation_prompt()

        # Format subtitles as JSON
        subtitles_data = [
            {
                "index": entry.index,
                "text": entry.text,
                "start": entry.start_time,
                "end": entry.end_time
            }
            for entry in batch
        ]
        subtitles_json = json.dumps(subtitles_data, ensure_ascii=False, indent=2)

        # Format the prompt
        prompt = template.format(
            source_language=source_lang,
            target_language=target_lang,
            count=len(batch),
            subtitles_json=subtitles_json
        )

        return prompt

    def _get_default_batch_translation_prompt(self) -> str:
        """Default batch translation prompt template."""
        return """Translate the following subtitle entries from {source_language} to {target_language}.

CRITICAL REQUIREMENTS:
1. Provide natural, contextual translations that capture meaning and emotion
2. Preserve the EXACT index order
3. Translate ALL {count} subtitle entries
4. DO NOT modify timestamps
5. Output ONLY valid JSON

INPUT SUBTITLES:
{subtitles_json}

OUTPUT FORMAT:
{{
  "translations": [
    {{"index": 1, "text": "Translated text", "start": "00:00:01,000", "end": "00:00:03,000"}},
    ...
  ]
}}
"""

    def _parse_batch_translation_response(
        self,
        response_text: str,
        original_batch: List[SubtitleEntry]
    ) -> List[SubtitleEntry]:
        """
        Parse batch translation response from LLM.

        Args:
            response_text: Raw response text from LLM
            original_batch: Original subtitle entries (for validation)

        Returns:
            List of translated SubtitleEntry objects

        Raises:
            ValueError: If response is invalid or incomplete
        """
        try:
            # Remove markdown code blocks if present
            cleaned_text = response_text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            elif cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()

            # Parse JSON
            data = json.loads(cleaned_text)

            # Validate required fields
            if 'translations' not in data:
                raise ValueError("Missing 'translations' field in response")

            translations = data['translations']

            # Validate count matches
            if len(translations) != len(original_batch):
                logger.warning(
                    f"Translation count mismatch: expected {len(original_batch)}, "
                    f"got {len(translations)}"
                )

            # Create SubtitleEntry objects
            translated_entries = []
            for i, trans in enumerate(translations):
                # Use original timing if translation doesn't include it
                original = original_batch[i] if i < len(original_batch) else None

                entry = SubtitleEntry(
                    index=trans.get('index', i + 1),
                    text=trans['text'],
                    start_time=trans.get('start', original.start_time if original else "00:00:00,000"),
                    end_time=trans.get('end', original.end_time if original else "00:00:01,000")
                )
                translated_entries.append(entry)

            return translated_entries

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse translation response as JSON: {e}")
            logger.error(f"Response text: {response_text[:500]}...")
            raise ValueError(f"Invalid JSON in translation response: {e}")
        except KeyError as e:
            logger.error(f"Missing required field in translation: {e}")
            raise ValueError(f"Invalid translation format: missing {e}")
        except Exception as e:
            logger.error(f"Error parsing translation response: {e}")
            raise
