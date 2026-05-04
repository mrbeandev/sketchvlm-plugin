# sketchvlm-plugin

A Claude Code plugin that lets your **current** Claude session draw on images while answering questions about them. Drop in a maze, a screenshot, a chart, or any photo, ask a visual-reasoning question, and get back the answer plus an SVG overlay that shows you *where* and *how* the model arrived at it.

**No API key. No extra billing.** The host model running your Claude Code session does the vision and the stroke planning — this plugin only ships the deterministic grid overlay and SVG rendering tools that turn the model's coordinate output into a real annotated image.

Implements the technique from the **SketchVLM** paper (Collins et al., 2026, [arXiv:2604.22875](https://arxiv.org/abs/2604.22875), CC BY 4.0). This is an independent implementation written from the paper; it does not bundle or depend on the original research codebase.

---

## What you get

- A `/sketchvlm:annotate` skill, plus a model-invokable skill that triggers automatically when you ask Claude to "annotate", "trace", "sketch on", "mark up", "circle the differences", or "highlight" something on an image.
- Two MCP tools — both are **pure deterministic Python** (no LLM calls inside):
  - `prepare_image(image_path, ...)` — overlays a labeled coordinate grid on a copy of the image. The host model `Read`s it, plans strokes, then sends them to the second tool.
  - `render_strokes(original_image_path, strokes_xml, ..., preview=True)` — composites the model's stroke XML as an SVG over the original image. Defaults to **preview mode** so the model can iterate before committing.
- **Preview-and-iterate workflow.** Vision models drift several percent of image dimensions when estimating coordinates; the skill mandates rendering, looking, and iterating before showing the user. Two or three preview rounds catch misalignments cheaply.
- **Pixel coords as well as grid coords.** When the model has algorithmic output (BFS path, OpenCV contours, NumPy diff), it uses `pxN,pyN` tokens directly — no lossy quantization to grid cells.
- **Seven stroke primitives.** Lines, smooth Bezier curves, arrows, rectangles, circles, ellipses, text labels. Multi-point curves are fitted with a single cubic Bezier via least-squares.
- **Top-left origin by default** (raster convention, matches how you actually read screenshots and photos). Pass `origin="bottom_left"` for math convention.
- **2× scale option** for dense grids so axis labels survive viewer downscaling.

---

## Install

### Prerequisites

- Claude Code (latest)
- [`uv`](https://docs.astral.sh/uv/) — used to run the MCP server in an isolated Python environment without polluting your system Python. Install with `curl -LsSf https://astral.sh/uv/install.sh | sh`.

That's it. **No API key needed.** The plugin uses the model already running your Claude Code session.

### From the marketplace (recommended)

In Claude Code:

```text
/plugin marketplace add mrbeandev/sketchvlm-plugin
/plugin install sketchvlm@mrbeandev
```

The first tool call will install the Python dependencies into a `uv`-managed environment automatically.

### From a local clone (for development)

```bash
git clone https://github.com/mrbeandev/sketchvlm-plugin.git
cd sketchvlm-plugin
claude --plugin-dir .
```

---

## Use it

> Hey, can you annotate `examples/maze.png` and trace the shortest path from start to end?

The skill activates, your current Claude session looks at the gridded image, plans strokes, **previews** the result and self-corrects until the alignment is honest, then shows you the final annotated PNG inline alongside the answer.

For algorithmic-precision tasks (mazes, spot-the-differences, contour tracing), the model can compute pixel positions directly with NumPy / OpenCV and emit them as `pxN,pyN` tokens — bypassing the grid entirely when the host has better data than visual estimation.

---

## How it works

1. The skill tells Claude to call `prepare_image(path)`. The MCP server overlays a labeled coordinate grid (default 50×50, top-left origin, light tick lines every unit, labeled every 5) on a copy of the image and returns the path plus the coordinate ranges.
2. Claude opens the gridded image with the built-in `Read` tool — it sees the image visually with the labeled axes.
3. Claude plans one or more strokes using grid or pixel coordinates and writes them as XML tags.
4. The skill calls `render_strokes(..., preview=True)`. The MCP server parses the strokes, fits multi-point curves to cubic Beziers, alpha-composites the rendered SVG onto the **original** (non-gridded) image, and writes to a `previews/` subfolder.
5. Claude `Read`s the preview, checks alignment, and either iterates or finalizes with `preview=False`.
6. The final annotated PNG renders inline for the user alongside the answer.

The grid is the trick that makes vision-model coordinate references precise. Without it, models drift several percent of the image dimensions off target. With it, they can hit individual cells reliably — and pixel mode handles the cases where even a cell's worth of error is too much.

---

## Configuration

### `prepare_image`

| Argument       | Default              | What it does                                                            |
| -------------- | -------------------- | ----------------------------------------------------------------------- |
| `target_cols`  | `50`                 | Coordinate-grid columns shown to the model.                             |
| `target_rows`  | `50`                 | Coordinate-grid rows shown to the model.                                |
| `min_cell_px`  | `20`                 | Floor on cell size in pixels (the grid auto-coarsens for small images). |
| `origin`       | `top_left`           | y-axis direction. Set to `bottom_left` for math convention.             |
| `scale`        | `1`                  | Multiplier for the gridded image resolution. Set to `2` if labels are getting downscaled in your viewer. |
| `save_dir`     | `./sketchvlm-output` | Where the gridded copy gets written.                                    |

### `render_strokes`

| Argument                | Default              | What it does                                                       |
| ----------------------- | -------------------- | ------------------------------------------------------------------ |
| `original_image_path`   | required             | The un-gridded image to composite onto.                            |
| `strokes_xml`           | required             | The XML stroke output from the model.                              |
| `grid_cols`, `grid_rows`| required             | Must match what `prepare_image` returned.                          |
| `origin`                | `top_left`           | Match what `prepare_image` returned.                               |
| `preview`               | `True`               | `True` writes to `previews/`; set `False` for the final render.    |
| `save_dir`              | `./sketchvlm-output` | Root output folder.                                                |

---

## Stroke format reference

```xml
<s1 type="LINE"    color="#ff3b30" width="3">x12y8 x18y14</s1>
<s2 type="CURVE"   color="#0a84ff" width="3">x4y4 x9y10 x14y8 x20y12</s2>
<s3 type="ARROW"   color="#34c759" width="3">x10y10 x16y16</s3>
<s4 type="RECT"    color="#ffd60a" width="2">x6y6 x14y12</s4>
<s5 type="CIRCLE"  color="#ff9500" width="3" cx="20" cy="30" r="5"/>
<s6 type="ELLIPSE" color="#5856d6" width="3" cx="40" cy="40" rx="8" ry="4"/>
<s7 type="TEXT"    color="#000000" size="14" x="20" y="20">start</s7>
<s8 type="LINE"    color="#ff3b30" width="3">px315,py210 px540,py210</s8>
<answer>your concise final answer</answer>
```

Pixel mode uses `pxN,pyN` for point lists and `pcx`/`pcy`/`pr`/`prx`/`pry` for circle and ellipse attributes.

---

## Repository layout

```
sketchvlm-plugin/
├── .claude-plugin/
│   ├── plugin.json          # plugin manifest
│   └── marketplace.json     # single-repo marketplace catalog
├── .mcp.json                # MCP server registration (no API key)
├── server/
│   └── mcp_server.py        # FastMCP server: prepare_image + render_strokes
├── sketchvlm_lite/
│   ├── grid.py              # coordinate-grid overlay
│   ├── prompt.py            # stroke-format spec
│   ├── parser.py            # stroke + answer extractor
│   └── render.py            # Bezier fit, SVG render, composite
├── skills/annotate/SKILL.md # workflow the host Claude follows
├── examples/                # sample maze + generator
├── requirements.txt
├── pyproject.toml
├── LICENSE                  # MIT
└── NOTICE                   # paper citation
```

---

## Roadmap

- [ ] `inspect_at(image, gx, gy, radius)` — return a small crop centered at a coordinate so the model can verify "is grid (20, 58) actually on the bow?" before drawing 10 strokes there.
- [ ] Algorithmic helpers as opt-in tools: `solve_maze`, `image_diff`, `detect_color_blob`. Give the model precise anchors when the task is amenable to algorithms.
- [ ] Auto-detect anchor points during `prepare_image` (numbered dots on salient features) so strokes can reference "anchor 4" instead of axis estimation.
- [ ] Move the stroke-format spec to a one-time skill resource so it doesn't repeat on every `prepare_image` call.

Issues and PRs welcome at [github.com/mrbeandev/sketchvlm-plugin](https://github.com/mrbeandev/sketchvlm-plugin).

---

## License

MIT — see [LICENSE](LICENSE). Third-party academic attribution lives in [NOTICE](NOTICE).

---

## Citation

If you use this plugin in research or build on it, please cite the original paper that introduced the technique:

```bibtex
@misc{collins2026sketchvlmvisionlanguagemodels,
      title={SketchVLM: Vision language models can annotate images to
             explain thoughts and guide users},
      author={Brandon Collins and Logan Bolton and Hung Huy Nguyen and
              Mohammad Reza Taesiri and Trung Bui and Anh Totti Nguyen},
      year={2026},
      eprint={2604.22875},
      archivePrefix={arXiv},
      primaryClass={cs.CV},
      url={https://arxiv.org/abs/2604.22875},
}
```

The original research codebase (separate from this plugin) lives at [github.com/Brandon-Collins7/sketchvlm](https://github.com/Brandon-Collins7/sketchvlm).
