"""Coordinate-grid overlay for image annotation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Tuple

from PIL import Image, ImageDraw, ImageFont

Origin = Literal["bottom_left", "top_left"]


@dataclass(frozen=True)
class GridSpec:
    """Mapping between grid (x, y) coordinates and pixel positions on the original image.

    Pixel positions refer to the *original* image (not the gridded image), so
    rendered strokes composite cleanly onto the unmodified input.
    """

    cols: int
    rows: int
    cell_px: int
    image_w: int
    image_h: int
    origin: Origin = "bottom_left"

    @property
    def total_w(self) -> int:
        return self.cols * self.cell_px

    @property
    def total_h(self) -> int:
        return self.rows * self.cell_px

    def to_pixel(self, x: float, y: float) -> Tuple[float, float]:
        """Convert grid coords (x in [0, cols], y in [0, rows]) to image pixels.

        Pixel y is always measured from the top of the image (PIL/SVG convention).
        """
        sx = self.image_w / self.total_w
        sy = self.image_h / self.total_h
        px = x * self.cell_px * sx
        if self.origin == "bottom_left":
            py = (self.total_h - y * self.cell_px) * sy
        else:
            py = y * self.cell_px * sy
        return px, py


def _pick_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/Library/Fonts/Arial.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def add_grid_overlay(
    image: Image.Image,
    target_cols: int = 50,
    target_rows: int = 50,
    min_cell_px: int = 20,
    max_cell_px: int = 80,
    label_step: int = 5,
    margin_px: int = 56,
    origin: Origin = "bottom_left",
) -> Tuple[Image.Image, GridSpec]:
    """Render a labeled coordinate grid over a copy of the image.

    The grid is drawn directly on the image with tick labels along the left
    (y axis) and bottom (x axis) margins, leaving the original image content
    fully visible underneath.

    Returns the gridded image (RGB) and a GridSpec describing the mapping.
    """
    img = image.convert("RGB").copy()
    w, h = img.size

    cell_w = max(min_cell_px, min(max_cell_px, w // max(1, target_cols)))
    cell_h = max(min_cell_px, min(max_cell_px, h // max(1, target_rows)))
    cell = max(min_cell_px, min(cell_w, cell_h))

    cols = max(1, w // cell)
    rows = max(1, h // cell)

    canvas = Image.new("RGB", (w + margin_px, h + margin_px), color=(255, 255, 255))
    canvas.paste(img, (margin_px, 0))

    draw = ImageDraw.Draw(canvas, "RGBA")
    font = _pick_font(max(10, cell // 2))

    grid_color = (90, 90, 90, 110)
    axis_color = (30, 30, 30, 220)
    label_color = (30, 30, 30, 255)

    for c in range(cols + 1):
        x_px = margin_px + c * cell
        draw.line([(x_px, 0), (x_px, h)], fill=grid_color, width=1)
        if c % label_step == 0 and c <= cols:
            label = f"x{c}"
            draw.text((x_px + 2, h + 4), label, fill=label_color, font=font)

    for r in range(rows + 1):
        y_px_top = r * cell
        draw.line([(margin_px, y_px_top), (margin_px + w, y_px_top)], fill=grid_color, width=1)
        if r % label_step == 0 and r <= rows:
            if origin == "bottom_left":
                label = f"y{rows - r}"
            else:
                label = f"y{r}"
            draw.text((4, y_px_top + 2), label, fill=label_color, font=font)

    draw.line([(margin_px, 0), (margin_px, h)], fill=axis_color, width=2)
    draw.line([(margin_px, h), (margin_px + w, h)], fill=axis_color, width=2)

    spec = GridSpec(
        cols=cols,
        rows=rows,
        cell_px=cell,
        image_w=w,
        image_h=h,
        origin=origin,
    )
    return canvas, spec
