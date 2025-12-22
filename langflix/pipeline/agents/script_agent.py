"""
Script Agent: Enhanced Expression Extraction with Context Summarization
Show Bible-aware extraction + chunk summaries
"""
import logging
import json
from typing import List, Dict, Any, Optional
from pathlib import Path

from langflix.pipeline.models import ChunkResult
from langflix.core.llm_client import get_gemini_client
from langflix import settings

logger = logging.getLogger(__name__)


class ScriptAgent:
    """
    Script Agent that extracts expressions AND generates chunk summaries
    Uses Show Bible for speaker inference and context understanding
    """

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize Script Agent

        Args:
            model_name: LLM model to use (defaults to settings)
        """
        self.model_name = model_name or settings.get_model_name()
        self.client = get_gemini_client()

        # Load prompt template
        prompt_path = Path(__file__).parent.parent / "prompts" / "script_agent.txt"
        with open(prompt_path, 'r', encoding='utf-8') as f:
            self.prompt_template = f.read()

        logger.info(f"ScriptAgent initialized with model: {self.model_name}")

    def analyze_chunk(
        self,
        chunk_id: int,
        script_chunk: str,
        show_bible: str,
        language_level: str = "intermediate",
        max_expressions_per_chunk: int = 3
    ) -> ChunkResult:
        """
        Analyze a single script chunk with Show Bible context

        Args:
            chunk_id: Sequential chunk number
            script_chunk: The subtitle chunk text
            show_bible: Show Bible content for context
            language_level: Target difficulty level
            max_expressions_per_chunk: Max expressions to extract

        Returns:
            ChunkResult with expressions and chunk summary
        """
        logger.info(f"📝 Analyzing chunk {chunk_id} with Script Agent")

        # Get language level descriptions from settings
        language_level_descriptions = self._get_language_level_descriptions()

        # Build prompt
        prompt = self.prompt_template.format(
            show_bible=show_bible,
            language_level=language_level,
            language_level_descriptions=language_level_descriptions,
            chunk_id=chunk_id,
            script_chunk=script_chunk,
            max_expressions_per_chunk=max_expressions_per_chunk
        )

        # Call LLM
        try:
            response = self._call_llm(prompt)
            result_data = self._parse_response(response)

            # Create ChunkResult
            chunk_result = ChunkResult(
                chunk_id=chunk_id,
                chunk_summary=result_data.get("chunk_summary", ""),
                expressions=result_data.get("expressions", [])
            )

            logger.info(
                f"✅ Chunk {chunk_id} analyzed: "
                f"{len(chunk_result.expressions)} expressions, "
                f"summary: {len(chunk_result.chunk_summary)} chars"
            )

            return chunk_result

        except Exception as e:
            logger.error(f"❌ Failed to analyze chunk {chunk_id}: {e}")
            # Return empty result with error note in summary
            return ChunkResult(
                chunk_id=chunk_id,
                chunk_summary=f"[Error analyzing chunk: {str(e)}]",
                expressions=[]
            )

    def _call_llm(self, prompt: str) -> str:
        """
        Call LLM with the prepared prompt

        Args:
            prompt: Formatted prompt

        Returns:
            LLM response text
        """
        # Use existing Gemini client
        model = self.client.GenerativeModel(self.model_name)

        generation_config = {
            "temperature": settings.get_temperature(),
            "top_p": settings.get_top_p(),
            "top_k": settings.get_top_k(),
            "max_output_tokens": 8192,  # Allow larger responses for detailed summaries
        }

        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )

        return response.text

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """
        Parse LLM JSON response

        Args:
            response: Raw LLM response

        Returns:
            Parsed dictionary

        Raises:
            ValueError if parsing fails
        """
        # Clean response (remove markdown code blocks if present)
        cleaned = response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]  # Remove ```json
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]  # Remove ```
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]  # Remove ```
        cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response was: {response[:500]}...")
            raise ValueError(f"Invalid JSON response from LLM: {e}")

    def _get_language_level_descriptions(self) -> str:
        """
        Get language level descriptions from settings

        Returns:
            Formatted descriptions string
        """
        levels = settings.get_language_levels()

        descriptions = []
        for level, info in levels.items():
            desc = f"**{level.upper()}**: {info['description']}\nExamples: {info['examples']}"
            descriptions.append(desc)

        return "\n\n".join(descriptions)

    def analyze_chunks_batch(
        self,
        chunks: List[Dict[str, Any]],
        show_bible: str,
        language_level: str = "intermediate",
        max_expressions_per_chunk: int = 3,
        max_total_expressions: Optional[int] = None
    ) -> List[ChunkResult]:
        """
        Analyze multiple chunks in sequence

        Args:
            chunks: List of subtitle chunk dictionaries
            show_bible: Show Bible content
            language_level: Target difficulty level
            max_expressions_per_chunk: Max expressions per chunk
            max_total_expressions: Total expression limit (for test mode)

        Returns:
            List of ChunkResults
        """
        results = []
        total_expressions = 0

        for idx, chunk in enumerate(chunks):
            chunk_id = idx + 1

            # Check if we've hit the total expression limit (test mode)
            if max_total_expressions and total_expressions >= max_total_expressions:
                logger.info(
                    f"🛑 Reached max_total_expressions limit ({max_total_expressions}), "
                    f"stopping at chunk {chunk_id}"
                )
                break

            # Analyze chunk
            result = self.analyze_chunk(
                chunk_id=chunk_id,
                script_chunk=self._format_chunk_text(chunk),
                show_bible=show_bible,
                language_level=language_level,
                max_expressions_per_chunk=max_expressions_per_chunk
            )

            results.append(result)
            total_expressions += len(result.expressions)

        logger.info(
            f"📊 Batch analysis complete: "
            f"{len(results)} chunks processed, "
            f"{total_expressions} total expressions extracted"
        )

        return results

    def _format_chunk_text(self, chunk: Dict[str, Any]) -> str:
        """
        Format subtitle chunk for prompt

        Args:
            chunk: Subtitle chunk dictionary

        Returns:
            Formatted text
        """
        # Assuming chunk has structure like: [{"index": 1, "start": "...", "end": "...", "text": "..."}]
        if isinstance(chunk, list):
            lines = []
            for entry in chunk:
                start = entry.get('start', '')
                end = entry.get('end', '')
                text = entry.get('text', '')
                lines.append(f"[{start} --> {end}] {text}")
            return "\n".join(lines)
        else:
            # Fallback for other formats
            return str(chunk)


# Backward compatibility alias
ScriptAgentV3 = ScriptAgent
