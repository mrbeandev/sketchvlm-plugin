"""Render parsed strokes to SVG and composite onto the original image."""

from __future__ import annotations

import io
from typing import List, Tuple
from xml.sax.saxutils import escape as xml_escape

import numpy as np
from PIL import Image

from .grid import GridSpec
from .parser import Stroke


_ARROW_MARKER_ID = "svlm-arrow"


def _fit_cubic_bezier(points: List[Tuple[float, float]]) -> Tuple[
    Tuple[float, float], Tuple[float, float], Tuple[float, float], Tuple[float, float]
]:
    """Fit a single cubic Bezier through `points` via least squares."""
    pts = np.asarray(points, dtype=float)
    n = len(pts)
    if n < 2:
        raise ValueError("need at least 2 points")
    if n == 2:
        p0, p3 = pts[0], pts[1]
        p1 = p0 + (p3 - p0) / 3.0
        p2 = p0 + 2.0 * (p3 - p0) / 3.0
        return tuple(p0), tuple(p1), tuple(p2), tuple(p3)

    diffs = np.diff(pts, axis=0)
    seg_len = np.hypot(diffs[:, 0], diffs[:, 1])
    cum = np.concatenate([[0.0], np.cumsum(seg_len)])
    total = cum[-1] if cum[-1] > 0 else 1.0
    t = cum / total

    p0 = pts[0]
    p3 = pts[-1]

    one_t = 1.0 - t
    b1 = 3.0 * (one_t ** 2) * t
    b2 = 3.0 * one_t * (t ** 2)
    b0 = one_t ** 3
    b3 = t ** 3

    rhs = pts - np.outer(b0, p0) - np.outer(b3, p3)
    A = np.column_stack([b1, b2])

    sol_x, *_ = np.linalg.lstsq(A, rhs[:, 0], rcond=None)
    sol_y, *_ = np.linalg.lstsq(A, rhs[:, 1], rcond=None)
    p1 = np.array([sol_x[0], sol_y[0]])
    p2 = np.array([sol_x[1], sol_y[1]])
    return tuple(p0), tuple(p1), tuple(p2), tuple(p3)


def _project(stroke: Stroke, grid: GridSpec, x: float, y: float) -> Tuple[float, float]:
    """Project a stroke's coord into pixel space, respecting its coord space."""
    if stroke.space == "pixel":
        # Pixel coords come from the original-image space. If the stroke uses
        # bottom-left origin we still flip y here.
        py = (grid.image_h - y) if grid.origin == "bottom_left" else y
        return float(x), float(py)
    return grid.to_pixel(x, y)


def _project_radius(stroke: Stroke, grid: GridSpec, r: float, axis: str = "x") -> float:
    if stroke.space == "pixel":
        return float(r)
    if axis == "x":
        return float(r) * grid.cell_px * (grid.image_w / max(1, grid.total_w))
    return float(r) * grid.cell_px * (grid.image_h / max(1, grid.total_h))


def _stroke_to_svg(stroke: Stroke, grid: GridSpec) -> str:
    color = stroke.color
    width = max(1, int(stroke.width))

    if stroke.kind == "TEXT":
        if stroke.x is None or stroke.y is None or stroke.text is None:
            return ""
        px, py = _project(stroke, grid, stroke.x, stroke.y)
        size = stroke.size or 14
        return (
            f'<text x="{px:.2f}" y="{py:.2f}" fill="{color}" '
            f'font-size="{size}" font-family="Helvetica, Arial, sans-serif" '
            f'paint-order="stroke" stroke="white" stroke-width="2">'
            f'{xml_escape(stroke.text)}</text>'
        )

    if stroke.kind == "CIRCLE":
        if stroke.cx is None or stroke.cy is None or stroke.r is None:
            return ""
        cx, cy = _project(stroke, grid, stroke.cx, stroke.cy)
        r = _project_radius(stroke, grid, stroke.r, "x")
        return (
            f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" '
            f'fill="none" stroke="{color}" stroke-width="{width}"/>'
        )

    if stroke.kind == "ELLIPSE":
        if stroke.cx is None or stroke.cy is None or stroke.rx is None or stroke.ry is None:
            return ""
        cx, cy = _project(stroke, grid, stroke.cx, stroke.cy)
        rx = _project_radius(stroke, grid, stroke.rx, "x")
        ry = _project_radius(stroke, grid, stroke.ry, "y")
        return (
            f'<ellipse cx="{cx:.2f}" cy="{cy:.2f}" rx="{rx:.2f}" ry="{ry:.2f}" '
            f'fill="none" stroke="{color}" stroke-width="{width}"/>'
        )

    if not stroke.points:
        return ""

    pts_px = [_project(stroke, grid, x, y) for x, y in stroke.points]

    if stroke.kind == "RECT":
        (x0, y0), (x1, y1) = pts_px[0], pts_px[1]
        x_min, x_max = sorted((x0, x1))
        y_min, y_max = sorted((y0, y1))
        return (
            f'<rect x="{x_min:.2f}" y="{y_min:.2f}" '
            f'width="{x_max - x_min:.2f}" height="{y_max - y_min:.2f}" '
            f'fill="none" stroke="{color}" stroke-width="{width}"/>'
        )

    if stroke.kind in ("LINE", "ARROW") and len(pts_px) >= 2:
        (x0, y0), (x1, y1) = pts_px[0], pts_px[1]
        marker = f' marker-end="url(#{_ARROW_MARKER_ID})"' if stroke.kind == "ARROW" else ""
        return (
            f'<line x1="{x0:.2f}" y1="{y0:.2f}" x2="{x1:.2f}" y2="{y1:.2f}" '
            f'stroke="{color}" stroke-width="{width}" stroke-linecap="round"{marker}/>'
        )

    if stroke.kind == "CURVE":
        if len(pts_px) == 2:
            (x0, y0), (x1, y1) = pts_px
            return (
                f'<line x1="{x0:.2f}" y1="{y0:.2f}" x2="{x1:.2f}" y2="{y1:.2f}" '
                f'stroke="{color}" stroke-width="{width}" stroke-linecap="round"/>'
            )
        p0, p1, p2, p3 = _fit_cubic_bezier(pts_px)
        return (
            f'<path d="M {p0[0]:.2f} {p0[1]:.2f} '
            f'C {p1[0]:.2f} {p1[1]:.2f}, {p2[0]:.2f} {p2[1]:.2f}, '
            f'{p3[0]:.2f} {p3[1]:.2f}" '
            f'fill="none" stroke="{color}" stroke-width="{width}" '
            f'stroke-linecap="round"/>'
        )

    return ""


def build_svg(strokes: List[Stroke], grid: GridSpec) -> str:
    body_parts = [_stroke_to_svg(s, grid) for s in strokes]
    body = "\n  ".join(p for p in body_parts if p)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {grid.image_w} {grid.image_h}" '
        f'width="{grid.image_w}" height="{grid.image_h}">\n'
        f'  <defs>\n'
        f'    <marker id="{_ARROW_MARKER_ID}" viewBox="0 0 10 10" '
        f'refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">\n'
        f'      <path d="M 0 0 L 10 5 L 0 10 z" fill="context-stroke"/>\n'
        f'    </marker>\n'
        f'  </defs>\n'
        f'  {body}\n'
        f'</svg>'
    )


def composite_svg_on_image(svg_text: str, base: Image.Image) -> bytes:
    """Rasterise the SVG and alpha-composite it over `base`. Returns PNG bytes."""
    base_rgba = base.convert("RGBA")
    overlay = _rasterise_svg(svg_text, base.width, base.height)
    out = Image.alpha_composite(base_rgba, overlay)
    buf = io.BytesIO()
    out.convert("RGB").save(buf, format="PNG")
    return buf.getvalue()


def _rasterise_svg(svg_text: str, width: int, height: int) -> Image.Image:
    try:
        import cairosvg
    except Exception:
        return Image.new("RGBA", (width, height), (0, 0, 0, 0))
    png_bytes = cairosvg.svg2png(
        bytestring=svg_text.encode("utf-8"),
        output_width=width,
        output_height=height,
    )
    return Image.open(io.BytesIO(png_bytes)).convert("RGBA")


def render_strokes(
    strokes: List[Stroke],
    base_image: Image.Image,
    grid: GridSpec,
) -> Tuple[bytes, str]:
    svg_text = build_svg(strokes, grid)
    png_bytes = composite_svg_on_image(svg_text, base_image)
    return png_bytes, svg_text
