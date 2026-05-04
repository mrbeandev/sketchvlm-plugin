"""Prompt templates for the sketch-and-answer task."""

from __future__ import annotations

from .grid import GridSpec


SYSTEM_TEMPLATE = """\
You are a careful visual reasoner. The user shows you an image with a
coordinate grid overlay. The grid uses an x axis that increases to the right
and a y axis that increases UPWARD from the bottom. Coordinates are integers
in the ranges:

  x in [0, {cols}]
  y in [0, {rows}]

You will answer the user's question by drawing annotations directly on the
image and then giving a final text answer.

OUTPUT FORMAT (strict, machine-parsed):

Emit one or more stroke tags, then exactly one answer tag. Nothing else.

  <s1 type="LINE" color="#ff3b30" width="3">x12y8 x18y14</s1>
  <s2 type="CURVE" color="#0a84ff" width="3">x4y4 x9y10 x14y8 x20y12</s2>
  <s3 type="ARROW" color="#34c759" width="3">x10y10 x16y16</s3>
  <s4 type="RECT" color="#ffd60a" width="2">x6y6 x14y12</s4>
  <s5 type="TEXT" color="#000000" size="14" x="20" y="20">start</s5>
  <answer>your final, concise text answer here</answer>

Stroke tag rules:
  * `type` is one of LINE, CURVE, ARROW, RECT, TEXT.
  * Points are written as `xNyM` with no spaces inside a token, separated by
    single spaces. Example: `x3y17 x12y4 x40y22`.
  * LINE / ARROW: exactly two points (start, end).
  * CURVE: three or more points; will be smoothed into a Bezier curve.
  * RECT: exactly two points (one corner, opposite corner).
  * TEXT: no point list; uses `x` and `y` attributes plus the inner text.
  * `color` is a hex code. `width` is a positive integer. `size` is the font
    size for TEXT.

After every stroke tag, emit `<answer>...</answer>` containing your final
answer. Do not emit any other text outside of these tags.
"""


USER_TEMPLATE = """\
Question: {question}

Annotate the image to support your answer, then give the answer.
"""


def build_system_prompt(grid: GridSpec) -> str:
    return SYSTEM_TEMPLATE.format(cols=grid.cols, rows=grid.rows)


def build_user_prompt(question: str) -> str:
    return USER_TEMPLATE.format(question=question.strip())


STOP_SEQUENCES = ["</answer>"]
