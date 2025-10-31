"""
Slide generator for LangFlix

Creates silent (no audio track) or audio-backed slides with text overlays.
Default behavior preserves source background resolution; no forced 720p/1080p.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import ffmpeg

from langflix import settings

logger = logging.getLogger(__name__)


@dataclass
class SlideText:
    dialogue: str
    expression: str
    dialogue_trans: str
    expression_trans: str
    similar1: Optional[str] = None
    similar2: Optional[str] = None


def _get_background_input() -> tuple[str, str]:
    candidates = [
        Path("assets/education_slide_background.png"),
        Path("assets/education_slide_background.jpg"),
        Path("assets/background.png"),
        Path("assets/background.jpg"),
    ]
    for p in candidates:
        if p.exists():
            return str(p.resolve()), "image2"
    return "color=c=0x1a1a2e:size=1920x1080", "lavfi"


def _clean_for_draw(text: str, limit: int) -> str:
    if not isinstance(text, str):
        text = str(text)
    text = (
        text.replace("'", "")
        .replace('"', "")
        .replace(":", "")
        .replace(",", "")
        .replace("\\", "")
        .replace("\n", " ")
        .replace("\t", " ")
    )
    text = "".join(c for c in text if c.isprintable() and c not in "@#$%^&*+=|<>")
    text = " ".join(text.split())
    return text[:limit] if text else ""


def _esc_draw(text: str) -> str:
    return text.replace(":", "\\:").replace("'", "\\'")


def _font_size(key: str, default: int) -> int:
    try:
        v = settings.get_font_size(key)
        if isinstance(v, (int, float)):
            return int(v)
    except Exception:
        pass
    return default


def create_silent_slide(
    text: SlideText,
    duration: float,
    output_path: Path,
) -> Path:
    bg_input, bg_type = _get_background_input()

    d = _esc_draw(_clean_for_draw(text.dialogue, 100))
    e = _esc_draw(_clean_for_draw(text.expression, 100))
    dt = _esc_draw(_clean_for_draw(text.dialogue_trans, 100))
    et = _esc_draw(_clean_for_draw(text.expression_trans, 100))
    s1 = _esc_draw(_clean_for_draw(text.similar1 or "", 100)) if text.similar1 else None
    s2 = _esc_draw(_clean_for_draw(text.similar2 or "", 100)) if text.similar2 else None

    font_file_opt = ""
    try:
        font_file = settings.get_font_file(None)
        if font_file:
            font_file_opt = f"fontfile={font_file}:"
    except Exception:
        pass

    d_size = _font_size("expression_dialogue", 40)
    e_size = _font_size("expression", 58)
    dt_size = _font_size("expression_dialogue_trans", 36)
    et_size = _font_size("expression_trans", 48)
    sim_size = _font_size("similar", 32)

    filters = []
    if d:
        filters.append(
            f"drawtext=text='{d}':fontsize={d_size}:fontcolor=white:{font_file_opt}x=(w-text_w)/2:y=h/2-220:borderw=2:bordercolor=black"
        )
    if e:
        filters.append(
            f"drawtext=text='{e}':fontsize={e_size}:fontcolor=yellow:{font_file_opt}x=(w-text_w)/2:y=h/2-150:borderw=3:bordercolor=black"
        )
    if dt:
        filters.append(
            f"drawtext=text='{dt}':fontsize={dt_size}:fontcolor=white:{font_file_opt}x=(w-text_w)/2:y=h/2:borderw=2:bordercolor=black"
        )
    if et:
        filters.append(
            f"drawtext=text='{et}':fontsize={et_size}:fontcolor=yellow:{font_file_opt}x=(w-text_w)/2:y=h/2+70:borderw=3:bordercolor=black"
        )
    base_y = 160
    line_gap = 40
    if s1:
        filters.append(
            f"drawtext=text='{s1}':fontsize={sim_size}:fontcolor=white:{font_file_opt}x=(w-text_w)/2:y=h-{base_y}:borderw=1:bordercolor=black"
        )
    if s2:
        filters.append(
            f"drawtext=text='{s2}':fontsize={sim_size}:fontcolor=white:{font_file_opt}x=(w-text_w)/2:y=h-{base_y+line_gap}:borderw=1:bordercolor=black"
        )

    vf = ",".join(filters)

    # Build background input (no forced scale). If it's an image, loop with t=duration.
    if bg_type == "image2":
        v_in = ffmpeg.input(bg_input, loop=1, t=duration, f=bg_type)["v"]
    else:
        v_in = ffmpeg.input(bg_input, f=bg_type, t=duration)["v"]

    (
        ffmpeg
        .output(v_in, str(output_path), vf=vf, vcodec="libx264", t=duration)
        .overwrite_output()
        .run(quiet=True)
    )
    logger.info(f"Silent slide created: {output_path}")
    return output_path


