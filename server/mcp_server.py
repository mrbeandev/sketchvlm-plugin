"""MCP server exposing the sketch-and-answer tool to Claude Code."""

from __future__ import annotations

import base64
import os
import pathlib
import sys
import time
from typing import Optional

from mcp.server.fastmcp import FastMCP, Image

# Allow running directly via `python server/mcp_server.py` from the plugin root
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from sketchvlm_lite.pipeline import annotate as _annotate  # noqa: E402


mcp = FastMCP("sketchvlm")


def _resolve_save_dir(save_dir: Optional[str]) -> pathlib.Path:
    if save_dir:
        target = pathlib.Path(save_dir).expanduser().resolve()
    else:
        target = pathlib.Path.cwd() / "sketchvlm-output"
    target.mkdir(parents=True, exist_ok=True)
    return target


@mcp.tool()
def sketch_annotate(
    image_path: str,
    question: str,
    model: str = "claude-opus-4-5",
    save_dir: Optional[str] = None,
    target_cols: int = 50,
    target_rows: int = 50,
    origin: str = "bottom_left",
) -> dict:
    """Annotate an image with overlay strokes that explain the answer to a question.

    Sends the image plus the question to a vision-language model, asks the
    model to draw on the image and answer in text, then renders the model's
    strokes as an SVG overlay composited onto the original image.

    Args:
        image_path: Absolute or relative path to the input image (PNG / JPG).
        question: Plain-English question about the image.
        model: Anthropic vision model id. Defaults to claude-opus-4-5.
        save_dir: Where to write the annotated PNG and SVG. Defaults to ./sketchvlm-output.
        target_cols: Coordinate-grid columns the model sees (default 50).
        target_rows: Coordinate-grid rows the model sees (default 50).
        origin: "bottom_left" (default) or "top_left" for the y axis direction.

    Returns:
        A dict with the text answer, paths to the rendered files, and any parser warnings.
    """
    src = pathlib.Path(image_path).expanduser().resolve()
    if not src.exists():
        raise FileNotFoundError(f"Image not found: {src}")

    image_bytes = src.read_bytes()

    result = _annotate(
        image_bytes=image_bytes,
        question=question,
        model=model,
        target_cols=target_cols,
        target_rows=target_rows,
        origin=origin,
    )

    out_dir = _resolve_save_dir(save_dir)
    stem = f"{src.stem}_annotated_{int(time.time())}"
    png_path = out_dir / f"{stem}.png"
    svg_path = out_dir / f"{stem}.svg"

    png_path.write_bytes(result["png"])
    svg_path.write_text(result["svg"], encoding="utf-8")

    return {
        "answer": result["answer"],
        "annotated_png": str(png_path),
        "svg": str(svg_path),
        "warnings": result["warnings"],
        "model": model,
    }


@mcp.tool()
def sketch_annotate_inline(
    image_path: str,
    question: str,
    model: str = "claude-opus-4-5",
) -> list:
    """Same as `sketch_annotate` but returns the annotated image inline.

    Use this when the user wants to see the result immediately in the chat
    rather than saving it to disk. Returns a list with the text answer
    followed by the annotated image as an inline content block.
    """
    src = pathlib.Path(image_path).expanduser().resolve()
    if not src.exists():
        raise FileNotFoundError(f"Image not found: {src}")

    image_bytes = src.read_bytes()
    result = _annotate(
        image_bytes=image_bytes,
        question=question,
        model=model,
    )

    answer = result["answer"] or "(model returned no answer text)"
    img = Image(data=result["png"], format="png")
    return [f"Answer: {answer}", img]


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.stderr.write(
            "[sketchvlm] ANTHROPIC_API_KEY is not set. The server will start "
            "but tool calls will fail until the key is exported.\n"
        )
    mcp.run()


if __name__ == "__main__":
    main()
