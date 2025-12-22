"""
Aggregator Agent: Combines chunk summaries into Master Episode Summary
Uses cheaper/faster model since task is simpler text rewriting
"""
import logging
from typing import List
from pathlib import Path

from langflix.core.llm_client import get_gemini_client
from langflix import settings

logger = logging.getLogger(__name__)


class AggregatorAgent:
    """
    Aggregates micro-summaries from chunks into a cohesive episode narrative
    """

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        """
        Initialize Aggregator Agent

        Args:
            model_name: Model to use (defaults to cheaper Flash model)
        """
        self.model_name = model_name
        self.client = get_gemini_client()

        # Load prompt template
        prompt_path = Path(__file__).parent.parent / "prompts" / "aggregator.txt"
        with open(prompt_path, 'r', encoding='utf-8') as f:
            self.prompt_template = f.read()

        logger.info(f"AggregatorAgent initialized with model: {self.model_name}")

    def aggregate_summaries(self, chunk_summaries: List[str]) -> str:
        """
        Combine chunk summaries into a master episode summary

        Args:
            chunk_summaries: List of chronological chunk summaries

        Returns:
            Master episode summary text
        """
        if not chunk_summaries:
            logger.warning("No chunk summaries to aggregate")
            return "[No content to summarize]"

        logger.info(f"📊 Aggregating {len(chunk_summaries)} chunk summaries")

        # Format summaries for prompt
        formatted_summaries = self._format_summaries(chunk_summaries)

        # Build prompt
        prompt = self.prompt_template.format(chunk_summaries=formatted_summaries)

        # Call LLM
        try:
            master_summary = self._call_llm(prompt)

            logger.info(f"✅ Master summary created ({len(master_summary)} chars)")
            logger.debug(f"Master summary preview: {master_summary[:200]}...")

            return master_summary

        except Exception as e:
            logger.error(f"❌ Failed to aggregate summaries: {e}")
            # Return concatenated summaries as fallback
            fallback = " ".join(chunk_summaries)
            logger.warning(f"Using fallback: concatenated summaries ({len(fallback)} chars)")
            return fallback

    def _format_summaries(self, chunk_summaries: List[str]) -> str:
        """
        Format chunk summaries for prompt

        Args:
            chunk_summaries: List of summary strings

        Returns:
            Formatted text with numbered chunks
        """
        formatted_lines = []
        for idx, summary in enumerate(chunk_summaries, 1):
            formatted_lines.append(f"Chunk {idx}: {summary}")

        return "\n\n".join(formatted_lines)

    def _call_llm(self, prompt: str) -> str:
        """
        Call LLM with the aggregation prompt

        Args:
            prompt: Formatted prompt

        Returns:
            Master summary text
        """
        model = self.client.GenerativeModel(self.model_name)

        generation_config = {
            "temperature": 0.3,  # Lower temperature for more focused summarization
            "top_p": 0.8,
            "top_k": 40,
            "max_output_tokens": 2048,  # Enough for 200-400 word summary
        }

        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )

        return response.text.strip()
