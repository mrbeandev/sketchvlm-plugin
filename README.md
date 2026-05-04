# sketchvlm-plugin

A Claude Code plugin that lets your **current** Claude session draw on images while answering questions about them. Drop in a maze, a screenshot, a chart, or any photo, ask a visual-reasoning question, and get back the answer plus an SVG overlay that shows you *where* and *how* the model arrived at it.

**No API key. No extra billing.** The host model running your Claude Code session does the vision and the stroke planning — this plugin only ships the deterministic grid overlay and SVG rendering tools that turn the model's coordinate output into a real annotated image.

Implements the technique from the **SketchVLM** paper (Collins et al., 2026, [arXiv:2604.22875](https://arxiv.org/abs/2604.22875), CC BY 4.0). This is an independent implementation written from the paper; it does not bundle or depend on the original research codebase.

---

## What you get

- A `/sketchvlm:annotate` skill, plus a model-invokable skill that triggers automatically when you ask Claude to "annotate", "trace", "sketch on", "mark up", or "highlight" something on an image.
- Two MCP tools — both are **pure deterministic Python** (no LLM calls inside):
  - `prepare_image(image_path, ...)` — overlays a labeled coordinate grid on a copy of the image and returns the path so the host model can look at it with the built-in Read tool.
  - `render_strokes(original_image_path, strokes_xml, grid_cols, grid_rows, ...)` — composites the model's stroke XML as an SVG over the original image and returns the annotated PNG.
- Bottom-left coordinate grid by default (mathematician convention); flip to top-left for UI screenshots.
- Strokes supported: straight lines, smooth Bezier curves, arrows, rectangles, and text labels. Multi-point curves are fitted with a single cubic Bezier via least-squares.

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

### From a prompt

> Hey, can you annotate `examples/maze.png` and trace the shortest path from start to end?

The skill activates, your current Claude session looks at the image, plans the strokes, calls `render_strokes`, and shows you the annotated PNG inline.

### From the slash command

```text
/sketchvlm:annotate examples/maze.png "trace the shortest path from start to end"
```

---

## How it works

1. The skill tells Claude to call `prepare_image(path)`. The MCP server overlays a labeled coordinate grid (default 50×50, bottom-left origin) on a copy of the image and returns the path plus the coordinate ranges.
2. Claude opens the gridded image with the built-in `Read` tool — it sees the image visually with the labeled axes.
3. Claude plans one or more strokes (`LINE`, `CURVE`, `ARROW`, `RECT`, `TEXT`) using the grid coordinates, and writes them as XML tags.
4. The skill calls `render_strokes(original_path, stroke_xml, grid_cols, grid_rows)`. The MCP server parses the strokes, fits multi-point curves to cubic Beziers, and alpha-composites the rendered SVG onto the **original** (non-gridded) image.
5. The skill reads the annotated PNG back so it renders inline, and Claude states the answer.

The grid is the trick that makes vision-model coordinate references precise. Without it, models drift several percent of the image dimensions off target. With it, they can hit individual cells reliably.

---

## Configuration

| Argument       | Default              | What it does                                                          |
| -------------- | -------------------- | --------------------------------------------------------------------- |
| `target_cols`  | `50`                 | Coordinate-grid columns shown to the model.                           |
| `target_rows`  | `50`                 | Coordinate-grid rows shown to the model.                              |
| `min_cell_px`  | `20`                 | Floor on cell size in pixels (the grid auto-coarsens for small images). |
| `origin`       | `bottom_left`        | y-axis direction. Set to `top_left` for image / UI coordinates.       |
| `save_dir`     | `./sketchvlm-output` | Where the gridded copy and the annotated PNG + SVG get written.       |

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

- [ ] Multi-turn iterative refinement ("make the arrow red instead", "extend the path")
- [ ] No-grid mode for models that prefer raw images
- [ ] Custom palette + stroke-style overrides
- [ ] Support for batched / multi-image annotation in a single call

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
