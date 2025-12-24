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

    def __init__(self, model_name: Optional[str] = None, output_dir: Optional[str] = None, show_name: Optional[str] = None):
        """
        Initialize Script Agent

        Args:
            model_name: LLM model to use (defaults to settings)
            output_dir: Optional output directory for debug logs
            show_name: Show name (defaults to settings if not provided)
        """
        self.model_name = model_name or settings.get_llm_model_name()
        self.output_dir = output_dir
        self.show_name = show_name
        self.client = get_gemini_client()

        # Load prompt template
        # Load prompt template from settings (YAML)
        prompt_file = settings.get_content_selection_template_file()
        # Go up 3 levels: agents -> pipeline -> langflix -> prompts
        prompt_path = Path(__file__).parent.parent.parent / "prompts" / prompt_file
        
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
        target_script_chunk: str,
        show_bible: str,
        language_level: str = "intermediate",
        max_expressions_per_chunk: int = 3,
        target_language: Optional[str] = None,
        target_language_code: Optional[str] = None,
        source_language: Optional[str] = None,
        source_language_code: Optional[str] = None
    ) -> ChunkResult:
        """
        Analyze a single script chunk with Show Bible context

        Args:
            chunk_id: Sequential chunk number
            script_chunk: The source language subtitle chunk text
            target_script_chunk: The target language subtitle chunk text
            show_bible: Show Bible content for context
            language_level: Target difficulty level
            max_expressions_per_chunk: Max expressions to extract

        Returns:
            ChunkResult with expressions and chunk summary
        """
        logger.info(f"📝 Analyzing chunk {chunk_id} with Script Agent")

        # Get language level descriptions from settings
        language_level_descriptions = self._get_language_level_descriptions()

        # Get config values for prompt placeholders
        show_name = self.show_name or settings.get_show_name()  # Use instance show_name if available
        source_lang = source_language or settings.get_source_language_name()
        source_lang_code = source_language_code or settings.get_source_language_code()
        target_lang = target_language or settings.get_default_target_language()
        target_lang_code = target_language_code or settings.get_target_language_code()
        min_expr = settings.get_min_expressions_per_chunk()
        target_duration = settings.get_short_video_target_duration()

        # Build prompt with exact keys matching expression_analysis_prompt.yaml
        prompt = self.prompt_template.format(
            show_name=show_name,
            source_language=source_lang,
            source_language_code=source_lang_code,
            target_language=target_lang,
            target_language_code=target_lang_code,
            min_expressions=min_expr,
            max_expressions=max_expressions_per_chunk,
            level_description=language_level_descriptions,  # Maps to {level_description}
            target_duration=target_duration,
            source_dialogues=script_chunk,                  # Maps to {source_dialogues}
            target_dialogues=target_script_chunk,           # Maps to {target_dialogues}

            # Legacy/Unused params (kept if template uses them unexpectedly)
            show_bible=show_bible,
            language_level=language_level,
            chunk_id=chunk_id,
            script_chunk=script_chunk
        )

        logger.info(f"🚀 Prompting LLM for {source_lang} -> {target_lang} (Expressions: {min_expr}-{max_expressions_per_chunk})")

        # Call LLM
        try:
            response = self._call_llm(prompt)
            result_data = self._parse_response(response)

            # Parse subtitle lines from script_chunk to get timestamps
            subtitle_lines = self._parse_script_chunk_times(script_chunk)
            target_subtitle_lines = self._parse_script_chunk_times(target_script_chunk) if target_script_chunk else []
            
            logger.debug(f"Parsed {len(subtitle_lines)} source lines and {len(target_subtitle_lines)} target lines")
            
            if subtitle_lines:
                logger.debug(f"First subtitle: idx=0, {subtitle_lines[0]['start_time']} -> {subtitle_lines[0]['end_time']}")
                logger.debug(f"Last subtitle: idx={len(subtitle_lines)-1}, {subtitle_lines[-1]['start_time']} -> {subtitle_lines[-1]['end_time']}")
            

            # Convert index-based expressions to timestamp-based AND construct dialogues
            expressions = result_data.get("expressions", [])
            for i, expr in enumerate(expressions):
                logger.debug(f"Expression {i+1} raw keys: {list(expr.keys())}")
                logger.debug(f"Expression {i+1} before conversion: start={expr.get('context_start_time', 'N/A')}, start_idx={expr.get('context_start_index', 'N/A')}, expr_idx={expr.get('expression_index', 'N/A')}")
                
                expr = self._convert_indices_to_timestamps(
                    expr=expr, 
                    subtitle_lines=subtitle_lines,
                    target_subtitle_lines=target_subtitle_lines,
                    source_lang_code=source_language_code or "en",
                    target_lang_code=target_language_code or "ko"
                )
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
        # Create a NEW dict to avoid mutating shared/cached config
        base_config = settings.get_generation_config()
        generation_config = {
            **base_config,  # Spread existing config
        }
        
        # Log config at INFO level for visibility during debugging
        logger.info(f"🔧 ScriptAgent LLM config: max_output_tokens={generation_config.get('max_output_tokens')}")

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
        
        # Save prompt and response for debugging
        import time
        if self.output_dir:
            debug_dir = Path(self.output_dir) / "debug"
        else:
            debug_dir = Path(__file__).parent.parent / "artifacts" / "debug"
            
        debug_dir.mkdir(parents=True, exist_ok=True)
        timestamp = int(time.time())
        
        prompt_file = debug_dir / f"script_agent_prompt_{timestamp}.txt"
        with open(prompt_file, "w", encoding="utf-8") as f:
            f.write(prompt)
        
        response_file = debug_dir / f"script_agent_response_{timestamp}.txt"
        with open(response_file, "w", encoding="utf-8") as f:
            f.write(text)
        
        logger.info(f"💾 Saved ScriptAgent host prompt to: {prompt_file.absolute()}")
        logger.info(f"💾 Saved ScriptAgent LLM response to: {response_file.absolute()}")
        
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
        target_chunks: List[Dict[str, Any]],
        show_bible: str,
        language_level: str = "intermediate",
        max_expressions_per_chunk: int = 3,
        max_total_expressions: Optional[int] = None,
        target_language: Optional[str] = None,
        target_language_code: Optional[str] = None,
        source_language: Optional[str] = None,
        source_language_code: Optional[str] = None
    ) -> List[ChunkResult]:
        """
        Analyze multiple chunks in sequence
        
        Args:
            chunks: List of source language subtitle chunk dictionaries
            target_chunks: List of target language subtitle chunk dictionaries
            show_bible: Show Bible content
            language_level: Target difficulty level
            max_expressions_per_chunk: Max expressions per chunk
            max_total_expressions: Total expression limit (for test mode)
            
        Returns:
            List of ChunkResults
        """
        results = []
        # Use generator internally
        generator = self.analyze_chunks_generator(
            chunks, target_chunks, show_bible, language_level,
            max_expressions_per_chunk, max_total_expressions,
            target_language, target_language_code,
            source_language, source_language_code
        )
        
        for result in generator:
            results.append(result)
            
        return results

    def analyze_chunks_generator(
        self,
        chunks: List[Dict[str, Any]],
        target_chunks: List[Dict[str, Any]],
        show_bible: str,
        language_level: str = "intermediate",
        max_expressions_per_chunk: int = 3,
        max_total_expressions: Optional[int] = None,
        target_language: Optional[str] = None,
        target_language_code: Optional[str] = None,
        source_language: Optional[str] = None,
        source_language_code: Optional[str] = None
    ):
        """
        Analyze multiple chunks in sequence yielding results
        """
        total_expressions = 0

        for idx, (chunk, target_chunk) in enumerate(zip(chunks, target_chunks)):
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
                target_script_chunk=self._format_chunk_text(target_chunk),
                show_bible=show_bible,
                language_level=language_level,
                max_expressions_per_chunk=max_expressions_per_chunk,
                target_language=target_language,
                target_language_code=target_language_code,
                source_language=source_language,
                source_language_code=source_language_code
            )

            # Truncate expressions if we've exceeded the total limit
            if max_total_expressions:
                remaining = max_total_expressions - total_expressions
                if remaining < len(result.expressions):
                    logger.info(
                        f"✂️ Truncating chunk {chunk_id} expressions from {len(result.expressions)} to {remaining} "
                        f"(max_total_expressions={max_total_expressions})"
                    )
                    result.expressions = result.expressions[:remaining]

            yield result
            total_expressions += len(result.expressions)

        logger.info(
            f"📊 Batch analysis complete: "
            f"{total_expressions} total expressions extracted"
        )

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
        # Pattern: [idx] [timestamp --> timestamp] text
        pattern = r'(?:\[\d+\]\s*)?\[([^\]]+)\s*-->\s*([^\]]+)\]\s*(.+)'
        
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
        subtitle_lines: List[Dict[str, str]],
        target_subtitle_lines: List[Dict[str, str]] = None,
        source_lang_code: str = "en",
        target_lang_code: str = "ko"
    ) -> Dict[str, Any]:
        """
        Convert LLM's index-based context to actual timestamps AND construct dialogues.
        
        Uses context_start_index and context_end_index from LLM response
        to look up actual timestamps from the parsed subtitle lines.
        
        Also programmatically constructs the 'dialogues' field to ensure
        accuracy and prevent LLM hallucinations (like repeating text).
        """
        if not subtitle_lines:
            logger.warning("No subtitle lines to convert indices")
            return expr
        
        max_idx = len(subtitle_lines) - 1
        
        # Get indices from LLM response - these are REQUIRED fields
        expr_idx = expr.get('expression_dialogue_index')
        start_idx = expr.get('context_start_index')
        end_idx = expr.get('context_end_index')
        
        # Validate required fields exist
        if expr_idx is None:
            raise ValueError(f"LLM response missing required field 'expression_dialogue_index': {expr}")
        if start_idx is None:
            raise ValueError(f"LLM response missing required field 'context_start_index': {expr}")
        if end_idx is None:
            raise ValueError(f"LLM response missing required field 'context_end_index': {expr}")
        
        # Validate indices are within subtitle range
        if not (0 <= expr_idx <= max_idx):
            raise ValueError(f"expression_dialogue_index={expr_idx} is out of range [0, {max_idx}]")
        if not (0 <= start_idx <= max_idx):
            raise ValueError(f"context_start_index={start_idx} is out of range [0, {max_idx}]")
        if not (0 <= end_idx <= max_idx):
            raise ValueError(f"context_end_index={end_idx} is out of range [0, {max_idx}]")
        if start_idx > end_idx:
            raise ValueError(f"context_start_index={start_idx} > context_end_index={end_idx}")
        
        # Clamp indices to valid ranges
        if start_idx < 0: start_idx = 0
        if end_idx >= len(subtitle_lines): end_idx = len(subtitle_lines) - 1
        if expr_idx >= len(subtitle_lines): expr_idx = len(subtitle_lines) - 1
        
        # After clamping, check for invalid range (e.g., start > end)
        if end_idx < start_idx:
            logger.error(f"❌ Failed to analyze chunk: Invalid context range [{start_idx}, {end_idx}] after clamping. Returning original expression.")
            return expr

        # CRITICAL: Validate expression_dialogue_index is within context bounds
        if expr_idx < start_idx or expr_idx > end_idx:
            logger.warning(
                f"expression_dialogue_index={expr_idx} is outside clamped context range [{start_idx}, {end_idx}]. "
                f"LLM must pick an expression FROM WITHIN the context. Clamping expr_idx to context start."
            )
            # If expr_idx is outside, clamp it to be within the context for robustness
            expr_idx = max(start_idx, min(expr_idx, end_idx))
            
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
        expr['expression_dialogue'] = subtitle_lines[expr_idx]['text']
        
        # Extract dialogue lines (Critical for Translation Service validation)
        expr['dialogue_lines'] = [line['text'] for line in subtitle_lines[start_idx : end_idx + 1]]
        
        # -------------------------------------------------------------------------
        # PROGRAMMATICALLY CONSTRUCT DIALOGUES (New Paired Format)
        # -------------------------------------------------------------------------
        # We REBUILD the dialogues as a list where each entry contains ALL language
        # translations paired together. This reduces LLM hallucination by keeping
        # translations aligned by index.
        #
        # New Format: [{"index": 0, "timestamp": "...", "en": "...", "ko": "..."}, ...]

        constructed_dialogues = []

        # Indices are relative to the chunk (0-based)
        # The 'index' field in the output should probably match the LLM's view (local index)
        # or global index if we had it. The prompt uses local indices [0..N].

        for i in range(start_idx, end_idx + 1):
            # Source Entry
            src_line = subtitle_lines[i]

            dialogue_entry = {
                "index": i,
                "timestamp": f"{src_line['start_time']} --> {src_line['end_time']}",
                source_lang_code: src_line['text']
            }

            # Target Entry (if file exists)
            # We assume 1-to-1 mapping by index for now (which is how the chunker works)
            if target_subtitle_lines and i < len(target_subtitle_lines):
                tgt_line = target_subtitle_lines[i]
                dialogue_entry[target_lang_code] = tgt_line['text']
            else:
                # No target subtitle file available
                # Try to get from LLM output (fallback for Legacy/Translation Mode)
                llm_dialogues = expr.get('dialogues', [])
                if isinstance(llm_dialogues, list):
                    # Check if LLM already returned the new format
                    for llm_entry in llm_dialogues:
                        if llm_entry.get("index") == i:
                            dialogue_entry[target_lang_code] = llm_entry.get(target_lang_code, "")
                            break
                    else:
                        dialogue_entry[target_lang_code] = ""
                else:
                    # LLM might still return old format, leave empty
                    dialogue_entry[target_lang_code] = ""

            constructed_dialogues.append(dialogue_entry)

        # Overwrite the LLM's dialogues with our robustly constructed ones
        expr['dialogues'] = constructed_dialogues
        
        logger.debug(
            f"Converted indices [{start_idx}-{end_idx}] to times "
            f"[{context_start_time} - {context_end_time}] and constructed dialogues"
        )
        
        return expr
