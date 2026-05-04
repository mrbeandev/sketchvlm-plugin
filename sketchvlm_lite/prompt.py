"""Stroke-format spec returned to the host model after grid preparation."""

from __future__ import annotations

from .grid import GridSpec


SPEC_TEMPLATE = """\
The grid uses x to the right and y UPWARD from the bottom. Coordinate ranges:
  x in [0, {cols}]
  y in [0, {rows}]

Produce one or more stroke tags, then exactly one answer tag:

  <s1 type="LINE"  color="#ff3b30" width="3">x12y8 x18y14</s1>
  <s2 type="CURVE" color="#0a84ff" width="3">x4y4 x9y10 x14y8 x20y12</s2>
  <s3 type="ARROW" color="#34c759" width="3">x10y10 x16y16</s3>
  <s4 type="RECT"  color="#ffd60a" width="2">x6y6 x14y12</s4>
  <s5 type="TEXT"  color="#000000" size="14" x="20" y="20">start</s5>
  <answer>your concise final answer</answer>

Rules:
  * type is one of LINE, CURVE, ARROW, RECT, TEXT.
  * Points are tokens like xNyM with no spaces inside, separated by single spaces.
  * LINE / ARROW: exactly two points (start, end).
  * CURVE: three or more points; smoothed into a Bezier curve.
  * RECT: exactly two opposite-corner points.
  * TEXT: no point list; uses x and y attributes plus the inner text.
  * color is a hex code; width is a positive integer; size is the TEXT font size.
"""


def build_stroke_spec(grid: GridSpec) -> str:
    """Return the human-readable stroke-format spec the host model should follow.

    The skill includes this string in its prompt to the host Claude after
    `prepare_image` reports the grid dimensions.
    """
    return SPEC_TEMPLATE.format(cols=grid.cols, rows=grid.rows)
