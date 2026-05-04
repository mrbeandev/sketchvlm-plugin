"""MCP server exposing deterministic grid + render helpers to Claude Code.

This server does NOT call any LLM. It only does the non-vision work:
  * `prepare_image`  — overlays a labeled coordinate grid for the host model
                       to look at. Returns the gridded path plus the stroke
                       format spec the model should follow.
  * `render_strokes` — takes the model's stroke XML and composites the
                       rendered SVG onto the ORIGINAL image (no grid),
                       returning the annotated PNG path. Defaults to PREVIEW
                       mode so the model can iterate before finalizing.

The host Claude Code session does the actual vision and stroke planning,
billed against the user's existing Claude Code subscription. No API key.
"""

from __future__ import annotations

import pathlib
import sys
import time
from typing import Optional

from mcp.server.fastmcp import FastMCP

# Allow running directly via `python server/mcp_server.py` from the plugin root
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from PIL import Image  # noqa: E402

from sketchvlm_lite.grid import GridSpec, add_grid_overlay  # noqa: E402
from sketchvlm_lite.parser import parse_response  # noqa: E402
from sketchvlm_lite.prompt import build_stroke_spec  # noqa: E402
from sketchvlm_lite.render import render_strokes as _render  # noqa: E402


mcp = FastMCP("sketchvlm")


def _output_dir(custom: Optional[str], subdir: Optional[str] = None) -> pathlib.Path:
    if custom:
        target = pathlib.Path(custom).expanduser().resolve()
    else:
        target = pathlib.Path.cwd() / "sketchvlm-output"
    if subdir:
        target = target / subdir
    target.mkdir(parents=True, exist_ok=True)
    return target


@mcp.tool()
def prepare_image(
    image_path: str,
    target_cols: int = 50,
    target_rows: int = 50,
    min_cell_px: int = 20,
    origin: str = "top_left",
    scale: int = 1,
    save_dir: Optional[str] = None,
) -> dict:
    """Overlay a labeled coordinate grid on a copy of the image and return the path.

    Call this first. Then Read the returned `gridded_image_path` so you can see
    the image visually with the coordinate axes labeled. Use those coordinates
    when planning strokes, then pass the original (un-gridded) `image_path` to
    `render_strokes` along with your stroke XML.

    Args:
        image_path: Absolute or relative path to the source image (PNG / JPG).
        target_cols: Target number of grid columns (default 50).
        target_rows: Target number of grid rows (default 50).
        min_cell_px: Minimum cell size in pixels (default 20).
        origin: "top_left" (default, raster convention) or "bottom_left"
            (mathematical convention).
        scale: Multiplier for the gridded image resolution. Set to 2 if the
            grid is dense enough that labels would otherwise be hard to read
            after viewer downscaling.
        save_dir: Where to write the gridded image (default ./sketchvlm-output).

    Returns:
        gridded_image_path: Path to the gridded image to Read.
        original_image_path: Path to pass to `render_strokes` for compositing.
        original_pixel_w, original_pixel_h: Native pixel dimensions of the
            original image (for stroke planning in pixel mode).
        grid_cols, grid_rows: Coordinate ranges available to the model.
        stroke_format_spec: Human-readable instructions to follow when emitting
            stroke XML for `render_strokes`.
    """
    src = pathlib.Path(image_path).expanduser().resolve()
    if not src.exists():
        raise FileNotFoundError(f"Image not found: {src}")

    img = Image.open(src).convert("RGB")
    gridded, spec = add_grid_overlay(
        img,
        target_cols=target_cols,
        target_rows=target_rows,
        min_cell_px=min_cell_px,
        origin=origin,  # type: ignore[arg-type]
        scale=scale,
    )

    out_dir = _output_dir(save_dir)
    grid_path = out_dir / f"{src.stem}_grid_{int(time.time())}.png"
    gridded.save(grid_path, format="PNG")

    return {
        "gridded_image_path": str(grid_path),
        "original_image_path": str(src),
        "original_pixel_w": img.width,
        "original_pixel_h": img.height,
        "grid_cols": spec.cols,
        "grid_rows": spec.rows,
        "origin": spec.origin,
        "stroke_format_spec": build_stroke_spec(spec),
    }


@mcp.tool()
def render_strokes(
    original_image_path: str,
    strokes_xml: str,
    grid_cols: int,
    grid_rows: int,
    origin: str = "top_left",
    preview: bool = True,
    save_dir: Optional[str] = None,
) -> dict:
    """Render stroke XML as an SVG overlay composited onto the original image.

    Pass the same `original_image_path` you got from `prepare_image`, plus the
    stroke tags you produced. `grid_cols` and `grid_rows` MUST match what
    `prepare_image` returned for this image so grid coordinates project correctly
    (pixel coordinates inside the strokes themselves bypass grid mapping).

    PREVIEW vs FINAL: by default this tool renders into a `previews/` subfolder
    so you can iterate without committing. Read the returned `annotated_png_path`
    to verify alignment. Call again with `preview=False` once you are satisfied
    to write the final output to the main folder.

    Args:
        original_image_path: The un-gridded source image to composite onto.
        strokes_xml: The full XML stroke output you produced (one or more
            <sN type=...> tags, optionally followed by an <answer> tag).
        grid_cols: Coordinate-x range used when planning grid-mode strokes.
        grid_rows: Coordinate-y range used when planning grid-mode strokes.
        origin: Same value passed to `prepare_image`. Default "top_left".
        preview: True (default) to render into a previews/ subfolder for
            iteration. Set False only for the final, user-facing render.
        save_dir: Root output folder (default ./sketchvlm-output).

    Returns:
        annotated_png_path: The composited PNG with strokes overlaid.
        svg_path: The standalone SVG overlay.
        answer: Text inside the <answer>...</answer> tag, if present.
        stroke_count: How many strokes were rendered.
        warnings: Any malformed strokes that were skipped.
        is_preview: True if this is a draft you should iterate on; False if
            it is the final the user will see.
    """
    src = pathlib.Path(original_image_path).expanduser().resolve()
    if not src.exists():
        raise FileNotFoundError(f"Image not found: {src}")

    img = Image.open(src).convert("RGB")
    spec = GridSpec(
        cols=grid_cols,
        rows=grid_rows,
        cell_px=max(1, img.width // max(1, grid_cols)),
        image_w=img.width,
        image_h=img.height,
        origin=origin,  # type: ignore[arg-type]
    )

    parsed = parse_response(strokes_xml)
    png_bytes, svg_text = _render(parsed.strokes, img, spec)

    subdir = "previews" if preview else None
    out_dir = _output_dir(save_dir, subdir=subdir)
    suffix = "_preview" if preview else ""
    stem = f"{src.stem}_annotated{suffix}_{int(time.time())}"
    png_path = out_dir / f"{stem}.png"
    svg_path = out_dir / f"{stem}.svg"
    png_path.write_bytes(png_bytes)
    svg_path.write_text(svg_text, encoding="utf-8")

    return {
        "annotated_png_path": str(png_path),
        "svg_path": str(svg_path),
        "answer": parsed.answer,
        "stroke_count": len(parsed.strokes),
        "warnings": parsed.warnings,
        "is_preview": preview,
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
