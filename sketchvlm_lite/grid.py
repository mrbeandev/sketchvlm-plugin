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
    origin: Origin = "top_left"

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
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/Library/Fonts/Arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
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
    origin: Origin = "top_left",
    scale: int = 1,
) -> Tuple[Image.Image, GridSpec]:
    """Render a labeled coordinate grid over a copy of the image.

    Light secondary tick lines are drawn every grid unit; heavier primary
    lines and labels every `label_step` units. The labels live in margins
    appended to the left and bottom edges; the original image content is left
    fully visible underneath.

    `scale` multiplies both the image and the label sizes — set to 2 for a
    higher-resolution gridded image when the grid is dense enough that labels
    would otherwise be hard to read after viewer downscaling.

    Returns the gridded image (RGB) and a GridSpec describing the mapping.
    """
    img = image.convert("RGB").copy()
    if scale != 1:
        img = img.resize((img.width * scale, img.height * scale), Image.LANCZOS)
    w, h = img.size

    cell_w = max(min_cell_px, min(max_cell_px, w // max(1, target_cols)))
    cell_h = max(min_cell_px, min(max_cell_px, h // max(1, target_rows)))
    cell = max(min_cell_px, min(cell_w, cell_h))

    cols = max(1, w // cell)
    rows = max(1, h // cell)

    label_size = max(12, int(cell * 0.7))
    margin_px = max(56, label_size * 4)
    font = _pick_font(label_size)

    canvas = Image.new("RGB", (w + margin_px, h + margin_px), color=(255, 255, 255))
    canvas.paste(img, (margin_px, 0))

    draw = ImageDraw.Draw(canvas, "RGBA")

    minor_color = (160, 160, 160, 70)
    major_color = (60, 60, 60, 160)
    axis_color = (20, 20, 20, 230)
    label_color = (15, 15, 15, 255)

    for c in range(cols + 1):
        x_px = margin_px + c * cell
        if c % label_step == 0:
            draw.line([(x_px, 0), (x_px, h)], fill=major_color, width=2)
            draw.text((x_px + 3, h + 4), f"x{c}", fill=label_color, font=font)
        else:
            draw.line([(x_px, 0), (x_px, h)], fill=minor_color, width=1)

    for r in range(rows + 1):
        y_px_top = r * cell
        if r % label_step == 0:
            draw.line(
                [(margin_px, y_px_top), (margin_px + w, y_px_top)],
                fill=major_color,
                width=2,
            )
            label_y = rows - r if origin == "bottom_left" else r
            draw.text((6, y_px_top + 2), f"y{label_y}", fill=label_color, font=font)
        else:
            draw.line(
                [(margin_px, y_px_top), (margin_px + w, y_px_top)],
                fill=minor_color,
                width=1,
            )

    draw.line([(margin_px, 0), (margin_px, h)], fill=axis_color, width=3)
    draw.line([(margin_px, h), (margin_px + w, h)], fill=axis_color, width=3)

    spec = GridSpec(
        cols=cols,
        rows=rows,
        cell_px=cell // scale if scale > 1 else cell,
        image_w=image.width,
        image_h=image.height,
        origin=origin,
    )
    return canvas, spec
