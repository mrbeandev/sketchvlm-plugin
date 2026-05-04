"""Parse the model's stroke + answer response into structured records."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Literal, Optional, Tuple

CoordSpace = Literal["grid", "pixel"]


_GRID_POINT = re.compile(r"\bx(-?\d+(?:\.\d+)?)y(-?\d+(?:\.\d+)?)")
_PIXEL_POINT = re.compile(r"\bpx(-?\d+(?:\.\d+)?)\s*,\s*py(-?\d+(?:\.\d+)?)")
_STROKE_BLOCK = re.compile(
    r"<s\d+\b([^>]*)/>|<s\d+\b([^>]*)>(.*?)</s\d+>",
    re.DOTALL | re.IGNORECASE,
)
_ATTR = re.compile(r"(\w+)\s*=\s*\"([^\"]*)\"")
_ANSWER = re.compile(r"<answer>(.*?)</answer>", re.DOTALL | re.IGNORECASE)


@dataclass
class Stroke:
    kind: str  # LINE, CURVE, ARROW, RECT, CIRCLE, ELLIPSE, TEXT
    points: List[Tuple[float, float]] = field(default_factory=list)
    color: str = "#ff3b30"
    width: int = 3
    space: CoordSpace = "grid"
    text: Optional[str] = None
    size: Optional[int] = None
    x: Optional[float] = None
    y: Optional[float] = None
    cx: Optional[float] = None
    cy: Optional[float] = None
    r: Optional[float] = None
    rx: Optional[float] = None
    ry: Optional[float] = None


@dataclass
class ParsedResponse:
    strokes: List[Stroke]
    answer: str
    warnings: List[str]


def _parse_attrs(raw: str) -> dict:
    return {k.lower(): v for k, v in _ATTR.findall(raw or "")}


def _parse_points(body: str) -> Tuple[List[Tuple[float, float]], CoordSpace]:
    """Pixel coords win when both formats appear in the same body."""
    pixel = [(float(x), float(y)) for x, y in _PIXEL_POINT.findall(body)]
    if pixel:
        return pixel, "pixel"
    grid = [(float(x), float(y)) for x, y in _GRID_POINT.findall(body)]
    return grid, "grid"


def _maybe_float(s: Optional[str]) -> Optional[float]:
    if s is None:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _maybe_int(s: Optional[str], default: int) -> int:
    if s is None:
        return default
    try:
        return int(float(s))
    except ValueError:
        return default


def _coord_from_attr(attrs: dict, key: str) -> Tuple[Optional[float], CoordSpace]:
    """Reads a coord from either grid (`x="20"`) or pixel (`px="315"`) attributes."""
    px_val = _maybe_float(attrs.get(f"p{key}"))
    if px_val is not None:
        return px_val, "pixel"
    return _maybe_float(attrs.get(key)), "grid"


def parse_response(text: str) -> ParsedResponse:
    """Extract strokes and the answer from the model's response.

    Tolerant of malformed strokes — anything that fails to parse is recorded
    in `warnings` rather than raising.
    """
    warnings: List[str] = []
    strokes: List[Stroke] = []

    for match in _STROKE_BLOCK.finditer(text):
        self_close_attrs = match.group(1)
        if self_close_attrs is not None:
            attrs_raw = self_close_attrs
            body = ""
        else:
            attrs_raw = match.group(2)
            body = match.group(3) or ""

        attrs = _parse_attrs(attrs_raw)
        kind = (attrs.get("type") or "LINE").upper()
        color = attrs.get("color", "#ff3b30")
        width = _maybe_int(attrs.get("width"), 3)
        attr_space = (attrs.get("space") or "").lower()

        if kind == "TEXT":
            tx, sx_space = _coord_from_attr(attrs, "x")
            ty, sy_space = _coord_from_attr(attrs, "y")
            if tx is None or ty is None:
                warnings.append(f"text stroke missing numeric x/y: {attrs}")
                continue
            space: CoordSpace = "pixel" if "pixel" in (sx_space, sy_space, attr_space) else "grid"
            size = _maybe_int(attrs.get("size"), 14)
            strokes.append(
                Stroke(
                    kind="TEXT",
                    color=color,
                    width=width,
                    text=body.strip(),
                    size=size,
                    x=tx,
                    y=ty,
                    space=space,
                )
            )
            continue

        if kind == "CIRCLE":
            cx, sxs = _coord_from_attr(attrs, "cx")
            cy, sys_ = _coord_from_attr(attrs, "cy")
            r = _maybe_float(attrs.get("r")) or _maybe_float(attrs.get("pr"))
            if cx is None or cy is None or r is None:
                warnings.append(f"circle stroke missing cx/cy/r: {attrs}")
                continue
            r_is_pixel = attrs.get("pr") is not None
            space = "pixel" if "pixel" in (sxs, sys_, attr_space) or r_is_pixel else "grid"
            strokes.append(
                Stroke(kind="CIRCLE", color=color, width=width, cx=cx, cy=cy, r=r, space=space)
            )
            continue

        if kind == "ELLIPSE":
            cx, sxs = _coord_from_attr(attrs, "cx")
            cy, sys_ = _coord_from_attr(attrs, "cy")
            rx = _maybe_float(attrs.get("rx")) or _maybe_float(attrs.get("prx"))
            ry = _maybe_float(attrs.get("ry")) or _maybe_float(attrs.get("pry"))
            if cx is None or cy is None or rx is None or ry is None:
                warnings.append(f"ellipse stroke missing cx/cy/rx/ry: {attrs}")
                continue
            radii_pixel = attrs.get("prx") is not None or attrs.get("pry") is not None
            space = "pixel" if "pixel" in (sxs, sys_, attr_space) or radii_pixel else "grid"
            strokes.append(
                Stroke(
                    kind="ELLIPSE",
                    color=color,
                    width=width,
                    cx=cx,
                    cy=cy,
                    rx=rx,
                    ry=ry,
                    space=space,
                )
            )
            continue

        pts, detected_space = _parse_points(body)
        space = "pixel" if attr_space == "pixel" else detected_space

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

        strokes.append(
            Stroke(kind=kind, points=pts, color=color, width=width, space=space)
        )

    answer_match = _ANSWER.search(text)
    answer = answer_match.group(1).strip() if answer_match else ""

    return ParsedResponse(strokes=strokes, answer=answer, warnings=warnings)
