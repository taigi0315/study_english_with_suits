"""
Pipeline Orchestrator: Contextual Localization Pipeline
Coordinates all agents to produce context-aware multilingual content
"""
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from langflix.pipeline.models import (
    EpisodeData,
    TranslationResult,
    PipelineConfig,
    ChunkResult
)
from langflix.pipeline.bible_manager import ShowBibleManager
from langflix.pipeline.agents.script_agent import ScriptAgent

logger = logging.getLogger(__name__)


class Pipeline:
    """
    Contextual Localization Pipeline

    Workflow:
    1. Phase 0: Get/Create Show Bible (Wikipedia)
    2. Phase 1: Extract expressions + Translate dialogues (Script Agent)

    Note: Translation is now handled by the Script Agent in Phase 1.
    Aggregator has been removed as episode_summary was not used anywhere.
    """

    def __init__(self, config: PipelineConfig):
        """
        Initialize Pipeline

        Args:
            config: Pipeline configuration
        """
        self.config = config

        # Initialize managers and agents
        self.bible_manager = ShowBibleManager()
        self.script_agent = ScriptAgent(output_dir=config.output_dir)

        logger.info(f"Pipeline initialized for show: {config.show_name}")

    def run(
        self,
        subtitle_chunks: List[Dict[str, Any]],
        target_subtitle_chunks: List[Dict[str, Any]],
        language_level: str = "intermediate",
        max_expressions_per_chunk: int = 3,
        max_total_expressions: Optional[int] = None
    ) -> EpisodeData:
        """
        Run the complete pipeline

        Args:
            subtitle_chunks: List of source language subtitle chunk dictionaries
            target_subtitle_chunks: List of target language subtitle chunk dictionaries
            language_level: Target difficulty level
            max_expressions_per_chunk: Max expressions per chunk
            max_total_expressions: Total expression limit (for test mode)

        Returns:
            EpisodeData with all results
        """
        logger.info("🚀 Starting Pipeline execution")

        # Phase 0: Get Show Bible
        show_bible = self._get_show_bible()
        if not show_bible:
            raise ValueError(f"Failed to get Show Bible for: {self.config.show_name}")

        # Phase 1: Extract + Translate
        logger.info("📝 Phase 1: Running Script Agent (includes expression extraction and dialogue translation)...")
        
        from langflix import settings
        target_lang_name = None
        target_lang_code = None
        
        if self.config.target_languages:
            target_lang_input = self.config.target_languages[0]
            # Try to resolve code and name
            if len(target_lang_input) <= 3:
                target_lang_code = target_lang_input.lower()
                target_lang_name = settings.language_code_to_name(target_lang_code) or target_lang_code.capitalize()
            else:
                target_lang_name = target_lang_input
                target_lang_code = settings.language_name_to_code(target_lang_name) or target_lang_input
        
        # Get source language code if possible
        source_lang_name = self.config.source_language
        source_lang_code = settings.language_name_to_code(source_lang_name) if source_lang_name else None

        chunk_results = self.script_agent.analyze_chunks_batch(
            chunks=subtitle_chunks,
            target_chunks=target_subtitle_chunks,
            show_bible=show_bible,
            language_level=language_level,
            max_expressions_per_chunk=max_expressions_per_chunk,
            max_total_expressions=max_total_expressions,
            target_language=target_lang_name,
            target_language_code=target_lang_code,
            source_language=source_lang_name,
            source_language_code=source_lang_code
        )

        # Create episode data
        episode_data = EpisodeData(
            episode_id=f"{self.config.show_name}_{self.config.episode_name}",
            show_name=self.config.show_name,
            show_bible=show_bible,
            chunks=chunk_results,
            master_summary=None  # No longer generated
        )

        logger.info(
            f"✅ Pipeline complete: "
            f"{len(chunk_results)} chunks, "
            f"{len(episode_data.get_all_expressions())} expressions"
        )

        return episode_data

    def translate_episode(
        self,
        episode_data: EpisodeData
    ) -> List[TranslationResult]:
        """
        DEPRECATED: Translation is now handled by Script Agent in run()
        This method now just converts expressions to TranslationResult format.

        Args:
            episode_data: Episode data from run()

        Returns:
            List of TranslationResult with multilingual data
        """
        logger.info("📦 Converting expressions to TranslationResult format...")

        # Get all expressions (now include dialogues with translations)
        all_expressions = episode_data.get_all_expressions()
        if not all_expressions:
            logger.warning("No expressions to convert")
            return []

        from langflix.pipeline.models import LocalizationData
        from langflix import settings
        
        # Convert into TranslationResult objects
        translation_results = []
        
        # Determine target language from config if available (maintains consistency with main.py)
        if self.config.target_languages:
            target_lang_input = self.config.target_languages[0]
            # Try to resolve code and name
            if len(target_lang_input) <= 3:
                target_lang_code = target_lang_input.lower()
                target_lang_name = settings.language_code_to_name(target_lang_code) or target_lang_code.capitalize()
            else:
                target_lang_name = target_lang_input
                target_lang_code = settings.language_name_to_code(target_lang_name) or target_lang_input
        else:
            # Fallback to settings
            target_lang_code = settings.get_target_language_code()
            target_lang_name = settings.get_default_target_language()

        for idx, expression in enumerate(all_expressions):
            # Find which chunk this expression came from
            chunk_id, chunk_summary = self._find_chunk_for_expression(
                idx, episode_data.chunks
            )

            # Extract localized dialogue if possible
            expr_dial_trans = ""
            expr_idx = expression.get("expression_dialogue_index")
            dialogues = expression.get("dialogues", {})
            
            # Robustness: Check if dialogues is actually a dict as expected by TranslationResult
            if not isinstance(dialogues, dict):
                logger.warning(f"Expression {idx} 'dialogues' is not a dict (got {type(dialogues)}). Using empty dict.")
                dialogues = {}

            if expr_idx is not None and isinstance(dialogues, dict) and target_lang_code in dialogues:
                for dial in dialogues[target_lang_code]:
                    if dial.get("index") == expr_idx:
                        expr_dial_trans = dial.get("text", "")
                        break

            # Create LocalizationData for the primary target language
            # This is required for backward compatibility with main.py and downstream services
            loc_data = LocalizationData(
                target_lang=target_lang_code,
                target_lang_name=target_lang_name,
                expression_translated=expression.get("expression_translation") or expression.get("expression_translated", ""),
                expression_dialogue_translated=expr_dial_trans,
                catchy_keywords_translated=expression.get("catchy_keywords", []),
                viral_title=expression.get("title") or expression.get("viral_title", ""),
                narrations=expression.get("narrations", []),
                vocabulary_annotations=expression.get("vocabulary_annotations", []),
                expression_annotations=expression.get("expression_annotations", []),
                translation_notes=expression.get("translation_notes", "")
            )

            # Create TranslationResult
            result = TranslationResult(
                expression=expression.get("expression", ""),
                expression_dialogue=expression.get("expression_dialogue", ""),
                context_summary_eng=expression.get("context_summary_eng"),
                start_time=expression.get("context_start_time", "00:00:00.000"),
                end_time=expression.get("context_end_time", "00:00:00.000"),
                expression_start_time=expression.get("expression_start_time"),
                expression_end_time=expression.get("expression_end_time"),
                dialogues=dialogues,
                scene_type=expression.get("scene_type"),
                similar_expressions=expression.get("similar_expressions", []),
                catchy_keywords=expression.get("catchy_keywords", []),
                chunk_id=chunk_id,
                chunk_summary=chunk_summary,
                episode_summary=None,
                localizations=[loc_data]
            )

            translation_results.append(result)

        logger.info(f"✅ Conversion complete: {len(translation_results)} expressions")
        return translation_results

    def _get_show_bible(self) -> str:
        """
        Get or create Show Bible

        Returns:
            Show Bible content
        """
        if not self.config.use_wikipedia:
            logger.info("Wikipedia disabled, using empty Show Bible")
            return f"=== SHOW BIBLE: {self.config.show_name} ===\n[No Wikipedia data]"

        logger.info(f"📖 Getting Show Bible for: {self.config.show_name}")

        bible = self.bible_manager.get_or_create_bible(
            show_name=self.config.show_name,
            force_refresh=not self.config.cache_show_bible
        )

        if not bible:
            logger.warning("Failed to create Show Bible, using minimal fallback")
            bible = f"=== SHOW BIBLE: {self.config.show_name} ===\n[Failed to retrieve data]"

        return bible

    def _find_chunk_for_expression(
        self,
        expression_idx: int,
        chunks: List[ChunkResult]
    ) -> tuple[int, str]:
        """
        Find which chunk an expression belongs to

        Args:
            expression_idx: Global expression index
            chunks: List of chunk results

        Returns:
            Tuple of (chunk_id, chunk_summary)
        """
        current_idx = 0
        for chunk in chunks:
            chunk_expr_count = len(chunk.expressions)
            if current_idx <= expression_idx < current_idx + chunk_expr_count:
                return chunk.chunk_id, chunk.chunk_summary
            current_idx += chunk_expr_count

        # Fallback
        return 1, chunks[0].chunk_summary if chunks else ""
