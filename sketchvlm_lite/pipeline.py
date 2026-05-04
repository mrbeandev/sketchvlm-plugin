"""End-to-end annotation pipeline."""

from __future__ import annotations

import io
from typing import Optional, TypedDict

from PIL import Image

from .grid import add_grid_overlay
from .parser import parse_response
from .prompt import STOP_SEQUENCES, build_system_prompt, build_user_prompt
from .providers import call_anthropic, encode_image_b64
from .render import render_strokes


class AnnotationResult(TypedDict):
    png: bytes
    svg: str
    answer: str
    raw: str
    warnings: list[str]


def annotate(
    image_bytes: bytes,
    question: str,
    model: str = "claude-opus-4-7",
    target_cols: int = 50,
    target_rows: int = 50,
    min_cell_px: int = 20,
    origin: str = "bottom_left",
    max_tokens: int = 4000,
    api_key: Optional[str] = None,
) -> AnnotationResult:
    """Run the full annotate-and-answer pipeline on a single image.

    Returns a dict with the rendered annotated PNG, the raw SVG overlay, the
    model's text answer, the raw model response, and any parser warnings.
    """
    base = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    gridded, spec = add_grid_overlay(
        base,
        target_cols=target_cols,
        target_rows=target_rows,
        min_cell_px=min_cell_px,
        origin=origin,  # type: ignore[arg-type]
    )

    buf = io.BytesIO()
    gridded.save(buf, format="PNG")
    grid_b64 = encode_image_b64(buf.getvalue())

    system = build_system_prompt(spec)
    user = build_user_prompt(question)

    raw = call_anthropic(
        model=model,
        system=system,
        image_b64=grid_b64,
        user_text=user,
        max_tokens=max_tokens,
        stop_sequences=STOP_SEQUENCES,
        media_type="image/png",
        api_key=api_key,
    )

    parsed = parse_response(raw)
    png, svg = render_strokes(parsed.strokes, base, spec)

    return AnnotationResult(
        png=png,
        svg=svg,
        answer=parsed.answer,
        raw=raw,
        warnings=parsed.warnings,
    )
