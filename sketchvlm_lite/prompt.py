"""Stroke-format spec returned to the host model after grid preparation."""

from __future__ import annotations

from .grid import GridSpec


_AXIS_NOTE_BOTTOM_LEFT = (
    "AXIS WARNING: this image uses BOTTOM-LEFT origin. y increases UPWARD. "
    "Features near the TOP of the picture have HIGH y values; features near "
    "the BOTTOM have LOW y values. Re-anchor your mental model before reading coords."
)
_AXIS_NOTE_TOP_LEFT = (
    "Origin is top-left (raster convention). y increases DOWNWARD; features "
    "near the top of the picture have LOW y values."
)


SPEC_TEMPLATE = """\
{axis_note}

Coordinate ranges (grid mode):
  x in [0, {cols}]
  y in [0, {rows}]

You may emit coordinates in EITHER format on a per-stroke basis:

  * Grid coords (default): tokens like `xNyM` (e.g. `x12y8`). Use these when
    you are reading positions visually off the grid labels.
  * Pixel coords: tokens like `pxN,pyM` (e.g. `px315,py210`). Use these when
    you already have exact pixel positions from algorithmic analysis (BFS,
    contour detection, OpenCV, etc.) — they bypass grid quantization.

Produce one or more stroke tags, then exactly one answer tag:

  <s1 type="LINE"    color="#ff3b30" width="3">x12y8 x18y14</s1>
  <s2 type="CURVE"   color="#0a84ff" width="3">x4y4 x9y10 x14y8 x20y12</s2>
  <s3 type="ARROW"   color="#34c759" width="3">x10y10 x16y16</s3>
  <s4 type="RECT"    color="#ffd60a" width="2">x6y6 x14y12</s4>
  <s5 type="CIRCLE"  color="#ff9500" width="3" cx="20" cy="30" r="5"/>
  <s6 type="ELLIPSE" color="#5856d6" width="3" cx="40" cy="40" rx="8" ry="4"/>
  <s7 type="TEXT"    color="#000000" size="14" x="20" y="20">start</s7>
  <s8 type="LINE"    color="#ff3b30" width="3">px315,py210 px540,py210</s8>
  <answer>your concise final answer</answer>

Rules:
  * type is one of LINE, CURVE, ARROW, RECT, CIRCLE, ELLIPSE, TEXT.
  * Stroke types with point lists: LINE/ARROW need 2 points, CURVE needs 2+
    (3+ are smoothed into a Bezier), RECT needs 2 opposite corners.
  * CIRCLE uses cx, cy, r attributes (or pcx, pcy, pr for pixel mode).
  * ELLIPSE uses cx, cy, rx, ry attributes (or pcx, pcy, prx, pry).
  * TEXT uses x, y attributes (or px, py for pixel mode) plus the inner text.
  * color is a hex code; width is a positive integer; size is the TEXT font size.
  * Mixing grid and pixel within a single stroke is allowed but discouraged —
    pick one format per stroke.

PRECISION TIP: vision models drift several percent of image dimensions when
estimating coordinates. Always preview your strokes before finalizing — call
`render_strokes` with `preview=True`, Read the result, and iterate until the
alignment is right. Only call `preview=False` once you are satisfied.
"""


def build_stroke_spec(grid: GridSpec) -> str:
    """Return the human-readable stroke-format spec the host model should follow."""
    axis_note = (
        _AXIS_NOTE_BOTTOM_LEFT if grid.origin == "bottom_left" else _AXIS_NOTE_TOP_LEFT
    )
    return SPEC_TEMPLATE.format(axis_note=axis_note, cols=grid.cols, rows=grid.rows)
