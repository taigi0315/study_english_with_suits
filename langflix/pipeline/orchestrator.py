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
from langflix.pipeline.agents.aggregator import AggregatorAgent
from langflix.pipeline.agents.translator import TranslatorAgent

logger = logging.getLogger(__name__)


class Pipeline:
    """
    Contextual Localization Pipeline

    Workflow:
    1. Phase 0: Get/Create Show Bible (Wikipedia)
    2. Phase 1: Extract expressions + Generate chunk summaries (Script Agent)
    3. Phase 2: Aggregate summaries into Master Summary (Aggregator)
    4. Phase 3: Translate with full context (Translator)
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
        self.script_agent = ScriptAgent()
        self.aggregator = AggregatorAgent(model_name=config.aggregator_model)
        self.translator = TranslatorAgent(model_name=config.translator_model)

        logger.info(f"Pipeline initialized for show: {config.show_name}")

    def run(
        self,
        subtitle_chunks: List[Dict[str, Any]],
        language_level: str = "intermediate",
        max_expressions_per_chunk: int = 3,
        max_total_expressions: Optional[int] = None
    ) -> EpisodeData:
        """
        Run the complete pipeline

        Args:
            subtitle_chunks: List of subtitle chunk dictionaries
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

        # Phase 1: Extract + Summarize
        logger.info("📝 Phase 1: Running Script Agent...")
        chunk_results = self.script_agent.analyze_chunks_batch(
            chunks=subtitle_chunks,
            show_bible=show_bible,
            language_level=language_level,
            max_expressions_per_chunk=max_expressions_per_chunk,
            max_total_expressions=max_total_expressions
        )

        # Phase 2: Aggregate Summaries
        logger.info("📊 Phase 2: Running Aggregator...")
        chunk_summaries = [chunk.chunk_summary for chunk in chunk_results]
        master_summary = self.aggregator.aggregate_summaries(chunk_summaries)

        # Create episode data
        episode_data = EpisodeData(
            episode_id=f"{self.config.show_name}_{self.config.episode_name}",
            show_name=self.config.show_name,
            show_bible=show_bible,
            chunks=chunk_results,
            master_summary=master_summary
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
        Translate episode expressions to all target languages

        Args:
            episode_data: Episode data from run()

        Returns:
            List of TranslationResult with multilingual data
        """
        if not self.config.target_languages:
            logger.warning("No target languages specified, skipping translation")
            return []

        logger.info(f"🌐 Phase 3: Translating to {len(self.config.target_languages)} languages")

        # Get all expressions
        all_expressions = episode_data.get_all_expressions()
        if not all_expressions:
            logger.warning("No expressions to translate")
            return []

        # Translate to all target languages
        translations_by_lang = self.translator.translate_to_multiple_languages(
            expressions=all_expressions,
            show_bible=episode_data.show_bible,
            master_summary=episode_data.master_summary or "",
            target_languages=self.config.target_languages
        )

        # Combine into TranslationResult objects
        translation_results = []

        for idx, expression in enumerate(all_expressions):
            # Find which chunk this expression came from
            chunk_id, chunk_summary = self._find_chunk_for_expression(
                idx, episode_data.chunks
            )

            # Collect localizations for this expression
            localizations = []
            for lang in self.config.target_languages:
                lang_localizations = translations_by_lang.get(lang, [])
                if idx < len(lang_localizations):
                    localizations.append(lang_localizations[idx])

            # Create TranslationResult
            result = TranslationResult(
                expression=expression.get("expression", ""),
                expression_dialogue=expression.get("expression_dialogue", ""),
                context_summary_eng=expression.get("context_summary_eng"),
                start_time=expression.get("context_start_time", "00:00:00.000"),
                end_time=expression.get("context_end_time", "00:00:00.000"),
                scene_type=expression.get("scene_type"),
                similar_expressions=expression.get("similar_expressions", []),
                catchy_keywords=expression.get("catchy_keywords", []),
                chunk_id=chunk_id,
                chunk_summary=chunk_summary,
                episode_summary=episode_data.master_summary,
                localizations=localizations
            )

            translation_results.append(result)

        logger.info(f"✅ Translation complete: {len(translation_results)} expressions")
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


# Backward compatibility aliases
V3Pipeline = Pipeline
