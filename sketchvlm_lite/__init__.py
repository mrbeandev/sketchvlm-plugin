"""Deterministic helpers for grid-anchored image annotation.

The actual vision-language reasoning is performed by whichever Claude model
is running the host Claude Code session — this package only handles the
non-LLM work (grid overlay, stroke parsing, SVG rendering, compositing).
"""

from .grid import GridSpec, add_grid_overlay
from .parser import ParsedResponse, Stroke, parse_response
from .prompt import build_stroke_spec
from .render import build_svg, composite_svg_on_image, render_strokes

__all__ = [
    "GridSpec",
    "add_grid_overlay",
    "ParsedResponse",
    "Stroke",
    "parse_response",
    "build_stroke_spec",
    "build_svg",
    "composite_svg_on_image",
    "render_strokes",
]
__version__ = "0.3.0"
