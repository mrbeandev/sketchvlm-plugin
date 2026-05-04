"""Parse the model's stroke + answer response into structured records."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


_POINT_TOKEN = re.compile(r"x(-?\d+(?:\.\d+)?)y(-?\d+(?:\.\d+)?)")
_STROKE_BLOCK = re.compile(
    r"<s\d+\b([^>]*)>(.*?)</s\d+>",
    re.DOTALL | re.IGNORECASE,
)
_TEXT_BLOCK = re.compile(
    r"<s\d+\b([^>]*\btype\s*=\s*[\"']text[\"'][^>]*)>(.*?)</s\d+>",
    re.DOTALL | re.IGNORECASE,
)
_ATTR = re.compile(r"(\w+)\s*=\s*\"([^\"]*)\"")
_ANSWER = re.compile(r"<answer>(.*?)</answer>", re.DOTALL | re.IGNORECASE)


@dataclass
class Stroke:
    kind: str  # LINE, CURVE, ARROW, RECT, TEXT
    points: List[Tuple[float, float]] = field(default_factory=list)
    color: str = "#ff3b30"
    width: int = 3
    text: Optional[str] = None
    size: Optional[int] = None
    x: Optional[float] = None
    y: Optional[float] = None


@dataclass
class ParsedResponse:
    strokes: List[Stroke]
    answer: str
    warnings: List[str]


def _parse_attrs(raw: str) -> dict:
    return {k.lower(): v for k, v in _ATTR.findall(raw or "")}


def _parse_points(body: str) -> List[Tuple[float, float]]:
    return [(float(x), float(y)) for x, y in _POINT_TOKEN.findall(body)]


def parse_response(text: str) -> ParsedResponse:
    """Extract strokes and the answer from the model's response.

    Tolerant of malformed strokes — anything that fails to parse is recorded
    in `warnings` rather than raising.
    """
    warnings: List[str] = []
    strokes: List[Stroke] = []

    for match in _STROKE_BLOCK.finditer(text):
        attrs_raw, body = match.group(1), match.group(2)
        attrs = _parse_attrs(attrs_raw)
        kind = (attrs.get("type") or "LINE").upper()
        color = attrs.get("color", "#ff3b30")
        try:
            width = int(attrs.get("width", "3"))
        except ValueError:
            width = 3

        if kind == "TEXT":
            try:
                tx = float(attrs.get("x", "0"))
                ty = float(attrs.get("y", "0"))
            except ValueError:
                warnings.append(f"text stroke missing numeric x/y: {attrs}")
                continue
            try:
                size = int(attrs.get("size", "14"))
            except ValueError:
                size = 14
            strokes.append(
                Stroke(
                    kind="TEXT",
                    color=color,
                    width=width,
                    text=body.strip(),
                    size=size,
                    x=tx,
                    y=ty,
                )
            )
            continue

        pts = _parse_points(body)

        if kind in ("LINE", "ARROW") and len(pts) < 2:
            warnings.append(f"{kind} requires 2 points, got {len(pts)}")
            continue
        if kind == "RECT" and len(pts) < 2:
            warnings.append(f"RECT requires 2 corner points, got {len(pts)}")
            continue
        if kind == "CURVE" and len(pts) < 2:
            warnings.append(f"CURVE requires 2+ points, got {len(pts)}")
            continue

        if kind in ("LINE", "ARROW", "RECT"):
            pts = pts[:2]

        strokes.append(Stroke(kind=kind, points=pts, color=color, width=width))

    answer_match = _ANSWER.search(text)
    answer = answer_match.group(1).strip() if answer_match else ""

    return ParsedResponse(strokes=strokes, answer=answer, warnings=warnings)
