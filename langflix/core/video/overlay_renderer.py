"""
Overlay Renderer - Renders text overlays for short-form videos.

This module is responsible for:
- Adding viral title overlay (top of video)
- Adding catchy keywords (hashtag format)
- Adding narrations (timed commentary)
- Adding vocabulary annotations (word definitions with dual-font)
- Adding expression annotations (idiom/phrase explanations with dual-font)
- Escaping text for FFmpeg drawtext filter

Extracted from video_editor.py overlay sections (lines 889-1508)
"""

import logging
import os
import random
import re
import textwrap
from typing import List, Dict, Any, Optional, Tuple

from langflix.core.video.font_resolver import FontResolver
from langflix import settings

logger = logging.getLogger(__name__)


class OverlayRenderer:
    """
    Renders text overlays for short-form videos.

    Responsibilities:
    - Render viral title at top
    - Render catchy keywords (hashtags)
    - Render narrations with timing
    - Render vocabulary annotations (dual-font: source + target)
    - Render expression annotations (dual-font: source + target)
    - Escape text for FFmpeg drawtext filter

    Example:
        >>> renderer = OverlayRenderer(
        ...     source_language_code="ko",
        ...     target_language_code="es"
        ... )
        >>> video_stream = renderer.add_viral_title(
        ...     video_stream=stream,
        ...     viral_title="니까짓 게 날 죽여?",
        ...     settings=settings
        ... )
    """

    def __init__(
        self,
        source_language_code: str,
        target_language_code: str,
        font_resolver: Optional[FontResolver] = None
    ):
        """
        Initialize OverlayRenderer.

        Args:
            source_language_code: Source language for expressions (e.g., "ko")
            target_language_code: Target language for translations (e.g., "es")
            font_resolver: Optional FontResolver instance (created if not provided)
        """
        self.source_language_code = source_language_code
        self.target_language_code = target_language_code

        # Use provided or create FontResolver
        if font_resolver:
            self.font_resolver = font_resolver
        else:
            self.font_resolver = FontResolver(
                default_language_code=target_language_code,
                source_language_code=source_language_code
            )

        logger.info(
            f"OverlayRenderer initialized: "
            f"source={source_language_code}, target={target_language_code}"
        )

    def add_viral_title(
        self,
        video_stream,
        viral_title: str,
        settings,
        duration: float = 0.0
    ):
        """
        Add title overlay at top of video.

        Note: Despite the method name, this renders the 'title' field which is
        in the TARGET language (user's native language), not source language.

        Args:
            video_stream: FFmpeg video stream
            viral_title: Title text (in TARGET language)
            settings: Settings module for configuration
            duration: Display duration (0 = entire video)

        Returns:
            Video stream with title overlay

        Example:
            >>> stream = renderer.add_viral_title(stream, "¡Aprende esta expresión!", settings)
        """
        import ffmpeg

        if not viral_title:
            return video_stream

        # Wrap title using configurable chars per line
        title_chars_per_line = settings.get_viral_title_chars_per_line()
        wrapped_viral_title = textwrap.fill(viral_title, width=title_chars_per_line)
        escaped_viral_title = self.escape_drawtext_string(wrapped_viral_title)

        # Get settings
        viral_font_size = settings.get_viral_title_font_size()
        viral_y = settings.get_viral_title_y_position()
        viral_color = settings.get_viral_title_text_color()
        viral_border = settings.get_viral_title_border_width()
        viral_border_color = settings.get_viral_title_border_color()
        viral_duration = settings.get_viral_title_display_duration() if duration == 0 else duration

        viral_title_args = {
            'text': escaped_viral_title,
            'fontsize': viral_font_size,
            'fontcolor': viral_color,
            'x': '(w-text_w)/2',  # Center horizontally
            'y': viral_y,
            'borderw': viral_border,
            'bordercolor': viral_border_color,
            'line_spacing': 8
        }

        # Add timing if duration is specified (0 = entire video)
        if viral_duration > 0:
            viral_title_args['enable'] = f"between(t,0,{viral_duration:.2f})"

        # Use TARGET language font for title (title is in user's native language)
        target_font = self.font_resolver.get_target_font("title")
        if target_font and os.path.exists(target_font):
            viral_title_args['fontfile'] = target_font

        video_stream = ffmpeg.filter(video_stream, 'drawtext', **viral_title_args)
        logger.info(f"Added title overlay: '{viral_title[:50]}...'")

        return video_stream

    def add_catchy_keywords(
        self,
        video_stream,
        keywords: List[str],
        settings,
        target_width: int = 1080
    ):
        """
        Add hashtag keywords below viral title (comma-separated, with line wrapping).

        Args:
            video_stream: FFmpeg video stream
            keywords: List of keywords (in target language)
            settings: Settings module for configuration
            target_width: Video width for positioning

        Returns:
            Video stream with keyword overlays

        Example:
            >>> stream = renderer.add_catchy_keywords(
            ...     stream, ["aprendizaje", "idiomas", "coreano"], settings
            ... )
        """
        import ffmpeg

        if not keywords:
            return video_stream

        # Limit to 5 keywords (increased since comma-separated is more compact)
        keywords = keywords[:5]

        # Format keywords: add "#" prefix to each
        formatted_keywords = [f"#{keyword}" for keyword in keywords]

        # Get settings
        font_size = settings.get_keywords_font_size()
        y_position = settings.get_keywords_y_position()
        line_height_factor = settings.get_keywords_line_height_factor()
        line_height = int(font_size * line_height_factor)
        max_width_percent = settings.get_keywords_max_width_percent()
        max_width = target_width * max_width_percent

        # Get target language font for keywords
        keyword_font = self.font_resolver.get_target_font("keywords")

        # Character width estimate for line wrapping calculation
        char_width_estimate = font_size * 0.6
        comma_separator = ", "

        # Build lines with comma-separated keywords, wrapping when needed
        lines = []
        current_line = []
        current_line_width = 0

        for keyword in formatted_keywords:
            keyword_width = len(keyword) * char_width_estimate
            separator_width = len(comma_separator) * char_width_estimate if current_line else 0
            
            # Check if adding this keyword would exceed max width
            if current_line and (current_line_width + separator_width + keyword_width > max_width):
                # Start a new line
                lines.append(current_line)
                current_line = [keyword]
                current_line_width = keyword_width
            else:
                # Add to current line
                current_line.append(keyword)
                current_line_width += separator_width + keyword_width

        # Don't forget the last line
        if current_line:
            lines.append(current_line)

        # Generate a random color for each line (for visual variety)
        line_colors = []
        for line_idx, line in enumerate(lines):
            # Use first keyword of line as seed for consistent color
            random.seed(hash(line[0]) % (2**32))
            r = random.randint(100, 255)
            g = random.randint(100, 255)
            b = random.randint(100, 255)
            line_colors.append(f"0x{b:02x}{g:02x}{r:02x}")

        # Render each line
        for line_idx, (line_keywords, color) in enumerate(zip(lines, line_colors)):
            line_y = y_position + (line_idx * line_height)
            
            # Join keywords with comma separator
            line_text = comma_separator.join(line_keywords)
            escaped_line = self.escape_drawtext_string(line_text)

            keyword_args = {
                'text': escaped_line,
                'fontsize': font_size,
                'fontcolor': color,
                'x': '(w-text_w)/2',  # Center the line
                'y': line_y,
                'borderw': settings.get_keywords_border_width(),
                'bordercolor': settings.get_keywords_border_color()
            }

            if keyword_font and os.path.exists(keyword_font):
                keyword_args['fontfile'] = keyword_font

            video_stream = ffmpeg.filter(video_stream, 'drawtext', **keyword_args)

        logger.info(f"Added {len(keywords)} catchy keywords ({len(lines)} lines, comma-separated)")
        return video_stream

    def add_narrations(
        self,
        video_stream,
        narrations: List[Dict[str, Any]],
        dialogue_count: int,
        context_duration: float,
        settings
    ):
        """
        Add narration overlays at specified times.

        Args:
            video_stream: FFmpeg video stream
            narrations: List of narration dicts with text, dialogue_index, type
            dialogue_count: Number of dialogue lines (for timing calculation)
            context_duration: Total duration of context section
            settings: Settings module for configuration

        Returns:
            Video stream with narration overlays

        Example:
            >>> narrations = [
            ...     {"text": "¡Qué escena!", "dialogue_index": 0, "type": "reaction"}
            ... ]
            >>> stream = renderer.add_narrations(stream, narrations, 5, 30.0, settings)
        """
        import ffmpeg

        if not narrations or dialogue_count <= 0:
            return video_stream

        time_per_dialogue = context_duration / dialogue_count

        narr_y = settings.get_narrations_y_position()
        narr_duration = settings.get_narrations_duration()
        narr_font_size = settings.get_narrations_font_size()
        narr_border = settings.get_narrations_border_width()
        narr_border_color = settings.get_narrations_border_color()

        # Get target language font
        target_font = self.font_resolver.get_target_font("keywords")

        logger.info(f"Processing {len(narrations)} narration overlays")

        for idx, narr_item in enumerate(narrations[:6]):  # Max 6 narrations
            # Handle both dict and object
            if isinstance(narr_item, dict):
                narr_text = self._clean_html(narr_item.get('text', ''))
                narr_dialogue_idx = narr_item.get('dialogue_index', 0)
                narr_type = narr_item.get('type', 'commentary')
            else:
                narr_text = self._clean_html(getattr(narr_item, 'text', ''))
                narr_dialogue_idx = getattr(narr_item, 'dialogue_index', 0)
                narr_type = getattr(narr_item, 'type', 'commentary')

            if not narr_text:
                continue

            # Wrap narration text to configured chars per line
            narr_chars_per_line = settings.get_narrations_chars_per_line()
            narr_text = textwrap.fill(narr_text, width=narr_chars_per_line)

            # Get color based on narration type
            narr_color = settings.get_narrations_type_color(narr_type)

            # Timing
            narr_start = max(0, narr_dialogue_idx * time_per_dialogue)
            narr_end = narr_start + narr_duration

            escaped_narr = self.escape_drawtext_string(narr_text)

            narr_args = {
                'text': escaped_narr,
                'fontsize': narr_font_size,
                'fontcolor': narr_color,
                'x': '(w-text_w)/2',
                'y': narr_y,
                'borderw': narr_border,
                'bordercolor': narr_border_color,
                'line_spacing': 8,  # Required for multiline text
                'enable': f"between(t,{narr_start:.2f},{narr_end:.2f})",
            }

            if target_font and os.path.exists(target_font):
                narr_args['fontfile'] = target_font

            video_stream = ffmpeg.filter(video_stream, 'drawtext', **narr_args)
            logger.debug(f"Added narration [{narr_type}]: '{narr_text[:30]}' at t={narr_start:.2f}-{narr_end:.2f}s")

        logger.info(f"Added {len(narrations[:6])} narration overlays")
        return video_stream

    def add_vocabulary_annotations(
        self,
        video_stream,
        vocab_annotations: List[Dict[str, Any]],
        dialogue_count: int,
        context_duration: float,
        settings
    ):
        """
        Add vocabulary word overlays with dual-font rendering.

        Uses source language font for the word and target language font for translation.

        Args:
            video_stream: FFmpeg video stream
            vocab_annotations: List of vocab dicts with word, translation, dialogue_index
            dialogue_count: Number of dialogue lines
            context_duration: Total duration
            settings: Settings module for configuration

        Returns:
            Video stream with vocabulary overlays

        Example:
            >>> vocab = [{"word": "사랑", "translation": "amor", "dialogue_index": 0}]
            >>> stream = renderer.add_vocabulary_annotations(stream, vocab, 5, 30.0, settings)
        """
        import ffmpeg

        if not vocab_annotations or dialogue_count <= 0:
            return video_stream

        time_per_dialogue = context_duration / dialogue_count

        # Get dual fonts
        source_font, target_font = self.font_resolver.get_dual_fonts("vocabulary")

        # Layout Strategy: 4 fixed rotating positions for VOCABULARY
        # These positions are offset from expression annotations to avoid overlap
        ANNOTATION_POSITIONS = [
            (600, 440),  # Top-right (vocabulary row 1)
            (600, 500),  # Bottom-right (vocabulary row 2)
        ]
        
        font_size = settings.get_vocabulary_font_size()
        annot_duration = settings.get_vocabulary_duration()

        # Random colors for vocabulary
        voca_colors = ['#FFD700', '#00FF00', '#FF6B6B', '#00BFFF', '#FF69B4', '#FFA500']

        logger.info(f"Processing {len(vocab_annotations)} vocabulary annotations (4 rotating positions)")

        for idx, vocab_annot in enumerate(vocab_annotations[:5]):  # Max 5
            # Handle both dict and object
            if isinstance(vocab_annot, dict):
                word = self._clean_html(vocab_annot.get('word', ''))
                translation = self._clean_html(vocab_annot.get('translation', ''))
                dialogue_index = vocab_annot.get('dialogue_index', 0)
            else:
                word = self._clean_html(getattr(vocab_annot, 'word', ''))
                translation = self._clean_html(getattr(vocab_annot, 'translation', ''))
                dialogue_index = getattr(vocab_annot, 'dialogue_index', 0)

            if not word or not translation:
                continue

            # Timing
            annot_start = max(0, dialogue_index * time_per_dialogue)
            annot_end = annot_start + annot_duration

            # Get rotating position (cycle through 4 positions)
            pos_idx = idx % len(ANNOTATION_POSITIONS)
            rand_x, rand_y = ANNOTATION_POSITIONS[pos_idx]

            # Escape text
            escaped_word = self.escape_drawtext_string(word)
            escaped_translation = self.escape_drawtext_string(translation)

            # Random color
            random_color = random.choice(voca_colors)

            common_args = {
                'fontsize': font_size,
                'fontcolor': random_color,
                'borderw': settings.get_vocabulary_border_width(),
                'bordercolor': settings.get_vocabulary_border_color(),
                'enable': f"between(t,{annot_start:.2f},{annot_end:.2f})",
            }

            # VERTICAL STACK LAYOUT (avoids font width estimation issues)
            # Line 1: Source word (Korean)
            # Line 2: Indented translation (Spanish)
            
            line_spacing = int(font_size * 1.2)
            indent = "    "  # 4 spaces for translation

            # 1. Render SOURCE WORD
            word_args = {**common_args, 'text': escaped_word, 'x': rand_x, 'y': rand_y}
            if source_font and os.path.exists(source_font):
                word_args['fontfile'] = source_font
            video_stream = ffmpeg.filter(video_stream, 'drawtext', **word_args)

            # 2. Render TRANSLATION on next line (indented)
            trans_y = rand_y + line_spacing
            indented_translation = indent + escaped_translation
            trans_args = {**common_args, 'text': indented_translation, 'x': rand_x, 'y': trans_y}
            if target_font and os.path.exists(target_font):
                trans_args['fontfile'] = target_font
            video_stream = ffmpeg.filter(video_stream, 'drawtext', **trans_args)

            logger.debug(f"Added vocabulary: '{word}' / '{translation}' at x={rand_x}, y={rand_y}-{trans_y}")

        logger.info(f"Added {len(vocab_annotations[:5])} vocabulary annotations (vertical stack)")
        return video_stream

    def add_expression_annotations(
        self,
        video_stream,
        expr_annotations: List[Dict[str, Any]],
        dialogue_count: int,
        context_duration: float,
        settings
    ):
        """
        Add expression/idiom overlays with dual-font rendering.

        Uses source language font for expression and target font for translation.

        Args:
            video_stream: FFmpeg video stream
            expr_annotations: List of expression dicts
            dialogue_count: Number of dialogue lines
            context_duration: Total duration
            settings: Settings module for configuration

        Returns:
            Video stream with expression overlays

        Example:
            >>> exprs = [{"expression": "식은 죽 먹기", "translation": "pan comido", "dialogue_index": 1}]
            >>> stream = renderer.add_expression_annotations(stream, exprs, 5, 30.0, settings)
        """
        import ffmpeg

        if not expr_annotations or dialogue_count <= 0:
            return video_stream

        time_per_dialogue = context_duration / dialogue_count

        # Get settings
        expr_annot_font_size = settings.get_expression_annotations_font_size()
        expr_annot_duration = settings.get_expression_annotations_duration()
        expr_annot_color = settings.get_expression_annotations_text_color()
        expr_annot_border = settings.get_expression_annotations_border_width()
        expr_annot_border_color = settings.get_expression_annotations_border_color()

        # Get dual fonts
        source_font, target_font = self.font_resolver.get_dual_fonts("vocabulary")

        # Layout Strategy: 4 fixed rotating positions for EXPRESSION annotations
        # These positions are offset from vocabulary annotations to avoid overlap
        ANNOTATION_POSITIONS = [
            (40, 440),   # Top-left (expression row 1)
            (40, 500),   # Bottom-left (expression row 2)
        ]

        logger.info(f"Processing {len(expr_annotations)} expression annotations (4 rotating positions)")

        for idx, ea_item in enumerate(expr_annotations[:3]):  # Max 3
            # Handle both dict and object
            if isinstance(ea_item, dict):
                ea_expr = self._clean_html(ea_item.get('expression', ''))
                ea_trans = self._clean_html(ea_item.get('translation', ''))
                ea_dialogue_idx = ea_item.get('dialogue_index', 0)
            else:
                ea_expr = self._clean_html(getattr(ea_item, 'expression', ''))
                ea_trans = self._clean_html(getattr(ea_item, 'translation', ''))
                ea_dialogue_idx = getattr(ea_item, 'dialogue_index', 0)

            if not ea_expr:
                continue

            # Timing
            ea_start = max(0, ea_dialogue_idx * time_per_dialogue)
            ea_end = ea_start + expr_annot_duration

            # Get rotating position (cycle through 4 positions)
            pos_idx = idx % len(ANNOTATION_POSITIONS)
            ea_x, ea_y = ANNOTATION_POSITIONS[pos_idx]

            escaped_expr = self.escape_drawtext_string(ea_expr)
            escaped_trans = self.escape_drawtext_string(ea_trans) if ea_trans else ""

            common_args = {
                'fontsize': expr_annot_font_size,
                'fontcolor': expr_annot_color,
                'borderw': expr_annot_border,
                'bordercolor': expr_annot_border_color,
                'enable': f"between(t,{ea_start:.2f},{ea_end:.2f})",
            }

            # VERTICAL STACK LAYOUT (avoids font width estimation issues)
            # Line 1: Expression (source language)
            # Line 2: Indented translation (target language)
            
            line_spacing = int(expr_annot_font_size * 1.2)
            indent = "    "  # 4 spaces for translation

            # 1. Render EXPRESSION (source language)
            expr_args = {**common_args, 'text': escaped_expr, 'x': ea_x, 'y': ea_y}
            if source_font and os.path.exists(source_font):
                expr_args['fontfile'] = source_font
            video_stream = ffmpeg.filter(video_stream, 'drawtext', **expr_args)

            # 2. Render TRANSLATION on next line (indented)
            if ea_trans:
                trans_y = ea_y + line_spacing
                indented_trans = indent + escaped_trans
                trans_args = {**common_args, 'text': indented_trans, 'x': ea_x, 'y': trans_y}
                if target_font and os.path.exists(target_font):
                    trans_args['fontfile'] = target_font
                video_stream = ffmpeg.filter(video_stream, 'drawtext', **trans_args)

            logger.debug(f"Added expression annotation: '{ea_expr}' / '{ea_trans}' at y={ea_y}")

        logger.info(f"Added {len(expr_annotations[:3])} expression annotations (vertical stack)")
        return video_stream

    def add_expression_text(
        self,
        video_stream,
        expression_text: str,
        translation_text: str,
        settings
    ):
        """
        Add expression and translation text at bottom of video (static, entire video).

        Args:
            video_stream: FFmpeg video stream
            expression_text: Expression in source language
            translation_text: Translation in target language
            settings: Settings module for configuration

        Returns:
            Video stream with expression text overlay
        """
        import ffmpeg

        # Get configurable chars per line from settings
        chars_per_line = settings.get_expression_chars_per_line()
        
        def wrap_text(text, width=None):
            if width is None:
                width = chars_per_line
            return textwrap.fill(text, width=width)

        # Expression (source language)
        expression_text = self._clean_html(expression_text)
        wrapped_expression = wrap_text(expression_text)
        escaped_expression = self.escape_drawtext_string(wrapped_expression)

        expression_y = settings.get_expression_y_position()
        expression_font_size = settings.get_expression_font_size()
        expr_line_count = wrapped_expression.count('\n') + 1
        expr_height_px = expression_font_size * 1.2 * expr_line_count

        expr_args = {
            'text': escaped_expression,
            'fontsize': expression_font_size,
            'fontcolor': settings.get_expression_text_color(),
            'x': '(w-text_w)/2',
            'y': expression_y,
            'borderw': settings.get_expression_border_width(),
            'bordercolor': settings.get_expression_border_color(),
            'line_spacing': 10
        }

        source_font = self.font_resolver.get_source_font("expression")
        if source_font and os.path.exists(source_font):
            expr_args['fontfile'] = source_font

        video_stream = ffmpeg.filter(video_stream, 'drawtext', **expr_args)

        # Translation (target language)
        translation_text = self._clean_html(translation_text)
        # Use translation-specific chars_per_line
        translation_chars_per_line = settings.get_translation_chars_per_line()
        wrapped_translation = textwrap.fill(translation_text, width=translation_chars_per_line)
        escaped_translation = self.escape_drawtext_string(wrapped_translation)

        padding_between = 20
        translation_y = f"{expression_y}+{int(expr_height_px) + padding_between}"

        trans_args = {
            'text': escaped_translation,
            'fontsize': settings.get_translation_font_size(),
            'fontcolor': settings.get_translation_text_color(),
            'x': '(w-text_w)/2',
            'y': translation_y,
            'borderw': settings.get_translation_border_width(),
            'bordercolor': settings.get_translation_border_color(),
            'line_spacing': 10
        }

        target_font = self.font_resolver.get_target_font("translation")
        if target_font and os.path.exists(target_font):
            trans_args['fontfile'] = target_font

        video_stream = ffmpeg.filter(video_stream, 'drawtext', **trans_args)

        return video_stream

    def add_logo(
        self,
        video_stream,
        logo_path: str,
        position: str = "top-center",
        scale_height: int = 59,
        opacity: float = 0.5
    ):
        """
        Add logo overlay to video.

        Args:
            video_stream: FFmpeg video stream
            logo_path: Path to logo PNG file
            position: Position ("top-center", "top-right", etc.)
            scale_height: Logo height in pixels
            opacity: Logo opacity (0.0 - 1.0)

        Returns:
            Video stream with logo overlay
        """
        import ffmpeg

        if not os.path.exists(logo_path):
            logger.debug(f"Logo file not found: {logo_path}")
            return video_stream

        try:
            logo_input = ffmpeg.input(str(logo_path))
            logo_video = logo_input['v'].filter('scale', -1, scale_height)
            logo_video = logo_video.filter('format', 'rgba')
            logo_video = logo_video.filter(
                'geq', r='r(X,Y)', g='g(X,Y)', b='b(X,Y)', 
                a=f'{opacity}*alpha(X,Y)'
            )

            if position == "top-center":
                x = '(W-w)/2'
                y = 0
            elif position == "top-right":
                x = 'W-w-20'
                y = 20
            else:
                x = '(W-w)/2'
                y = 0

            video_stream = ffmpeg.overlay(
                video_stream,
                logo_video,
                x=x,
                y=y,
                enable='between(t,0,999999)'
            )

            logger.info(f"Added logo at {position} ({scale_height}px, {opacity*100}% opacity)")

        except Exception as e:
            logger.warning(f"Failed to add logo: {e}")

        return video_stream

    @staticmethod
    def escape_drawtext_string(text: str) -> str:
        """
        Escape text for FFmpeg drawtext filter.

        Args:
            text: Raw text string

        Returns:
            Escaped string safe for FFmpeg
        """
        if not text:
            return ""

        # Normalize quotes
        text = text.replace("'", "'").replace("'", "'").replace("‚", "'").replace("‛", "'")
        text = text.replace(""", '"').replace(""", '"').replace("„", '"')
        text = text.replace('"', '')  # Remove double quotes

        # Escape for FFmpeg drawtext
        escaped = text.replace("\\", "\\\\")
        escaped = escaped.replace(":", "\\:")
        escaped = escaped.replace("'", "\\'")
        escaped = escaped.replace("[", "\\[")
        escaped = escaped.replace("]", "\\]")

        return escaped

    @staticmethod
    def _clean_html(text: str) -> str:
        """Remove HTML tags from text."""
        if not text:
            return ""
        return re.sub(r'<[^>]+>', '', text)
