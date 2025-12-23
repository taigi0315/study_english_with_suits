"""
Script Agent: Enhanced Expression Extraction with Context Summarization
Show Bible-aware extraction + chunk summaries
"""
import logging
import json
import re
import yaml
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
        self.model_name = model_name or settings.get_llm_model_name()
        self.client = get_gemini_client()

        # Load prompt template
        # Load prompt template from settings (YAML)
        prompt_file = settings.get_content_selection_template_file()
        prompt_path = Path(__file__).parent.parent / "prompts" / prompt_file
        
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                if prompt_path.suffix in ('.yaml', '.yml'):
                    yaml_content = yaml.safe_load(f)
                    self.prompt_template = yaml_content.get('prompt', '')
                else:
                    self.prompt_template = f.read()
            logger.info(f"Loaded prompt template from: {prompt_path}")
        except Exception as e:
            logger.error(f"Failed to load prompt template {prompt_path}: {e}")
            raise

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
        # Get config values for prompt placeholders
        show_name = settings.get_show_name()
        source_lang = settings.get_source_language_name()
        target_lang = settings.get_default_target_language()
        min_expr = settings.get_min_expressions_per_chunk()
        target_duration = settings.get_short_video_target_duration()
        
        # Build prompt with exact keys matching expression_analysis_prompt.yaml
        prompt = self.prompt_template.format(
            show_name=show_name,
            source_language=source_lang,
            target_language=target_lang,
            min_expressions=min_expr,
            max_expressions=max_expressions_per_chunk,
            level_description=language_level_descriptions,  # Maps to {level_description}
            target_duration=target_duration,
            source_dialogues=script_chunk,                  # Maps to {source_dialogues}
            target_dialogues="(Target dialogues not available during analysis)", # Placeholder
            
            # Legacy/Unused params (kept if template uses them unexpectedly)
            show_bible=show_bible,
            language_level=language_level,
            chunk_id=chunk_id,
            script_chunk=script_chunk
        )

        # Call LLM
        try:
            response = self._call_llm(prompt)
            result_data = self._parse_response(response)

            # Parse subtitle lines from script_chunk to get timestamps
            subtitle_lines = self._parse_script_chunk_times(script_chunk)
            logger.debug(f"Parsed {len(subtitle_lines)} subtitle lines from chunk")
            if subtitle_lines:
                logger.debug(f"First subtitle: idx=0, {subtitle_lines[0]['start_time']} -> {subtitle_lines[0]['end_time']}")
                logger.debug(f"Last subtitle: idx={len(subtitle_lines)-1}, {subtitle_lines[-1]['start_time']} -> {subtitle_lines[-1]['end_time']}")
            

            # Convert index-based expressions to timestamp-based
            expressions = result_data.get("expressions", [])
            for i, expr in enumerate(expressions):
                logger.debug(f"Expression {i+1} raw keys: {list(expr.keys())}")
                logger.debug(f"Expression {i+1} before conversion: expr={expr}")
                logger.debug(f"Expression {i+1} before conversion: start={expr.get('context_start_time', 'N/A')}, start_idx={expr.get('context_start_index', 'N/A')}, expr_idx={expr.get('expression_index', 'N/A')}")
                expr = self._convert_indices_to_timestamps(expr, subtitle_lines)
                logger.debug(f"Expression {i+1} after conversion: start={expr.get('context_start_time', 'N/A')}, end={expr.get('context_end_time', 'N/A')}")

            # Create ChunkResult
            chunk_result = ChunkResult(
                chunk_id=chunk_id,
                chunk_summary=result_data.get("chunk_summary", ""),
                expressions=expressions
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
        # Get base config from settings and add max_output_tokens
        generation_config = settings.get_generation_config()
        generation_config["max_output_tokens"] = 8192  # Allow larger responses for detailed summaries

        # self.client is already a GenerativeModel from get_gemini_client()
        response = self.client.generate_content(
            prompt,
            generation_config=generation_config
        )

        # Check for empty or blocked response
        if not response:
            logger.error("LLM returned None response")
            raise ValueError("LLM returned empty response")
        
        # Check if response was blocked
        if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
            logger.warning(f"Prompt feedback: {response.prompt_feedback}")
        
        # Check candidates
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'finish_reason'):
                logger.info(f"Finish reason: {candidate.finish_reason}")
            if hasattr(candidate, 'safety_ratings'):
                for rating in candidate.safety_ratings:
                    if rating.probability.name != 'NEGLIGIBLE':
                        logger.warning(f"Safety rating: {rating.category.name} = {rating.probability.name}")
        
        # Get text - handle None
        text = getattr(response, 'text', None)
        if not text:
            logger.error("LLM response has no text content")
            logger.error(f"Response object: {response}")
            raise ValueError("LLM response has no text content")
        
        logger.debug(f"LLM response length: {len(text)} chars")
        return text

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """
        Parse LLM JSON response

        Args:
            response: Raw LLM response

        Returns:
            Parsed dictionary

        Raises:
            ValueError if parsing fails completely
        """
        import re
        
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
            # Log parsed data summary
            expressions_count = len(data.get("expressions", []))
            summary_length = len(data.get("chunk_summary", ""))
            logger.info(f"Parsed response: {expressions_count} expressions, {summary_length} char summary")
            if expressions_count == 0:
                logger.warning(f"LLM returned 0 expressions. Summary: {data.get('chunk_summary', 'N/A')[:200]}")
            return data
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse failed: {e}")
            
            # Try to recover chunk_summary even if expressions array is malformed
            try:
                # Extract chunk_summary using regex
                summary_match = re.search(r'"chunk_summary"\s*:\s*"([^"]+)"', cleaned, re.DOTALL)
                chunk_id_match = re.search(r'"chunk_id"\s*:\s*(\d+)', cleaned)
                
                if summary_match:
                    chunk_summary = summary_match.group(1)
                    chunk_id = int(chunk_id_match.group(1)) if chunk_id_match else 1
                    logger.info(f"Recovered chunk_summary ({len(chunk_summary)} chars) despite malformed JSON")
                    
                    # Return with empty expressions - at least we have the summary
                    return {
                        "chunk_id": chunk_id,
                        "chunk_summary": chunk_summary,
                        "expressions": []  # Can't recover expressions from malformed JSON
                    }
            except Exception as recovery_error:
                logger.error(f"Recovery also failed: {recovery_error}")
            
            logger.error(f"Response was: {response[:1000]}...")
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
            chunk: Subtitle chunk dictionary or list

        Returns:
            Formatted text
        """
        # Handle dict format from main.py: {'chunk_id': ..., 'script': '...', ...}
        if isinstance(chunk, dict):
            # If it has 'script' key, use that directly (already formatted)
            if 'script' in chunk:
                return chunk['script']
            # Legacy format with subtitle entries
            elif 'subtitles' in chunk:
                lines = []
                for entry in chunk['subtitles']:
                    start = entry.get('start_time', entry.get('start', ''))
                    end = entry.get('end_time', entry.get('end', ''))
                    text = entry.get('text', '')
                    lines.append(f"[{start} --> {end}] {text}")
                return "\n".join(lines)
        # Handle list format: [{"start": "...", "end": "...", "text": "..."}, ...]
        elif isinstance(chunk, list):
            lines = []
            for entry in chunk:
                start = entry.get('start', entry.get('start_time', ''))
                end = entry.get('end', entry.get('end_time', ''))
                text = entry.get('text', '')
                lines.append(f"[{start} --> {end}] {text}")
            return "\n".join(lines)
        
        # Fallback for string or other formats
        return str(chunk)

    def _parse_script_chunk_times(self, script_chunk: str) -> List[Dict[str, str]]:
        """
        Parse subtitle lines from script_chunk to extract timestamps.
        
        The script_chunk format is:
        [00:00:01,000 --> 00:00:02,500] Dialogue text here
        [00:00:03,000 --> 00:00:04,500] Another line
        
        Returns:
            List of dicts with 'start_time', 'end_time', 'text'
        """
        lines = []
        # Pattern: [timestamp --> timestamp] text
        pattern = r'\[([^\]]+)\s*-->\s*([^\]]+)\]\s*(.+)'
        
        for line in script_chunk.split('\n'):
            line = line.strip()
            if not line:
                continue
            match = re.match(pattern, line)
            if match:
                lines.append({
                    'start_time': match.group(1).strip(),
                    'end_time': match.group(2).strip(),
                    'text': match.group(3).strip()
                })
        
        return lines

    def _convert_indices_to_timestamps(
        self,
        expr: Dict[str, Any],
        subtitle_lines: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Convert LLM's index-based context to actual timestamps.
        
        Uses context_start_index and context_end_index from LLM response
        to look up actual timestamps from the parsed subtitle lines.
        
        If indices are missing or invalid, creates a sensible default
        context window around the expression.
        """
        if not subtitle_lines:
            logger.warning("No subtitle lines to convert indices")
            return expr
        
        max_idx = len(subtitle_lines) - 1
        
        # Get indices from LLM response (or defaults)
        expr_idx = expr.get('expression_index', 0)
        start_idx = expr.get('context_start_index', max(0, expr_idx - 3))
        end_idx = expr.get('context_end_index', min(max_idx, expr_idx + 3))
        
        # Clamp to valid range
        expr_idx = max(0, min(expr_idx, max_idx))
        start_idx = max(0, min(start_idx, max_idx))
        end_idx = max(start_idx, min(end_idx, max_idx))
        
        # Ensure minimum context window of ~10-15 seconds (at least 3 lines)
        if end_idx - start_idx < 3:
            start_idx = max(0, expr_idx - 3)
            end_idx = min(max_idx, expr_idx + 3)
        
        # Look up timestamps
        context_start_time = subtitle_lines[start_idx]['start_time']
        context_end_time = subtitle_lines[end_idx]['end_time']
        expression_start_time = subtitle_lines[expr_idx]['start_time']
        expression_end_time = subtitle_lines[expr_idx]['end_time']
        
        # Update expression dict with actual timestamps
        expr['context_start_time'] = context_start_time
        expr['context_end_time'] = context_end_time
        expr['expression_start_time'] = expression_start_time
        expr['expression_end_time'] = expression_end_time
        
        # Extract dialogue lines (Critical for Translation Service validation)
        expr['dialogues'] = [line['text'] for line in subtitle_lines[start_idx : end_idx + 1]]
        
        logger.debug(
            f"Converted indices [{start_idx}-{end_idx}] to times "
            f"[{context_start_time} - {context_end_time}]"
        )
        
        return expr
