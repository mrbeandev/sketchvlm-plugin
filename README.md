# sketchvlm-plugin

A Claude Code plugin that lets a vision-language model **draw on your image** while answering a question about it. Drop in a maze, a screenshot, a chart, or any photo, ask a visual-reasoning question, and get back the answer plus an SVG overlay that shows you *where* and *how* the model arrived at it.

Implements the technique from the **SketchVLM** paper (Collins et al., 2026, [arXiv:2604.22875](https://arxiv.org/abs/2604.22875), CC BY 4.0). This is an independent implementation written from the paper; it does not bundle or depend on the original research codebase.

---

## What you get

- A `/sketchvlm:annotate` skill, plus a model-invokable skill that triggers automatically when you ask Claude to "annotate", "trace", "sketch on", "mark up", or "highlight" something on an image.
- Two MCP tools:
  - `sketch_annotate_inline(image_path, question)` — returns the annotated PNG inline in the chat.
  - `sketch_annotate(image_path, question, save_dir=...)` — saves the annotated PNG and SVG to disk and returns the paths.
- Bottom-left coordinate-grid overlay sent to the model, with the strokes composited cleanly onto the **original** image (the grid is never burned into the output).
- Strokes supported: straight lines, smooth Bezier curves, arrows, rectangles, and text labels.

---

## Install

### Prerequisites

- Claude Code (latest)
- [`uv`](https://docs.astral.sh/uv/) — used to run the MCP server in an isolated Python environment without polluting your system Python. Install with `curl -LsSf https://astral.sh/uv/install.sh | sh`.
- An Anthropic API key exported as `ANTHROPIC_API_KEY`.

### From this marketplace (recommended)

In Claude Code:

```text
/plugin marketplace add mrbeandev/sketchvlm-plugin
/plugin install sketchvlm@mrbeandev
```

That's it. The first tool call will install the Python dependencies into a `uv`-managed environment automatically.

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

Claude will pick up the model-invokable skill, call `sketch_annotate_inline`, and reply with the answer text plus the annotated image inline.

### From the slash command

```text
/sketchvlm:annotate examples/maze.png "trace the shortest path from start to end"
```

### From your own Python (without the plugin)

```python
import pathlib
from sketchvlm_lite.pipeline import annotate

img = pathlib.Path("examples/maze.png").read_bytes()
result = annotate(img, "Trace the shortest path from start to end.")

pathlib.Path("out.png").write_bytes(result["png"])
print("Answer:", result["answer"])
```

---

## Configuration

| Argument       | Default            | What it does                                                                  |
| -------------- | ------------------ | ----------------------------------------------------------------------------- |
| `model`        | `claude-opus-4-5`  | Any Anthropic vision model. Try `claude-sonnet-4-5` for a faster, cheaper run. |
| `target_cols`  | `50`               | Coordinate-grid columns shown to the model.                                   |
| `target_rows`  | `50`               | Coordinate-grid rows shown to the model.                                      |
| `origin`       | `bottom_left`      | y-axis direction. Set to `top_left` for image-style coordinates.              |
| `save_dir`     | `./sketchvlm-output` | Where the saved variant writes the PNG + SVG.                                |

---

## How it works

1. The input image gets a labeled coordinate grid (left + bottom margins, default 50×50, bottom-left origin).
2. The gridded image is sent to the chosen Anthropic vision model with a strict output spec: emit `<sN type="...">x..y.. x..y..</sN>` stroke tags, then `<answer>...</answer>`.
3. The model's response is parsed: stroke types `LINE` / `CURVE` / `ARROW` / `RECT` / `TEXT` plus the answer text.
4. Each stroke is converted to SVG. Multi-point curves are fitted to a single cubic Bezier via least-squares, two-point strokes go straight to lines.
5. The SVG is rasterised and alpha-composited over the **original** (non-gridded) image, then returned to you as a PNG.

The grid is what makes coordinate references precise — without it, vision models tend to drift several percent of the image dimensions off target. With it, they can hit individual cells reliably.

---

## Repository layout

```
sketchvlm-plugin/
├── .claude-plugin/
│   ├── plugin.json          # plugin manifest
│   └── marketplace.json     # single-repo marketplace catalog
├── .mcp.json                # MCP server registration
├── server/
│   └── mcp_server.py        # FastMCP server exposing the two tools
├── sketchvlm_lite/          # the implementation
│   ├── grid.py              # coordinate-grid overlay
│   ├── prompt.py            # system + user prompt templates
│   ├── providers.py         # Anthropic vision client
│   ├── parser.py            # stroke + answer extractor
│   ├── render.py            # Bezier fit, SVG render, composite
│   └── pipeline.py          # annotate() end-to-end
├── skills/annotate/SKILL.md # model-invokable skill
├── examples/                # sample images
├── requirements.txt
├── pyproject.toml
├── LICENSE                  # MIT
└── NOTICE                   # paper citation
```

---

## Roadmap

- [ ] OpenAI (`gpt-4o`, `gpt-5-vision`) and Gemini provider support
- [ ] Multi-turn iterative refinement (paper's stepwise mode)
- [ ] No-grid mode for models that prefer raw images
- [ ] Custom palette + stroke-style overrides

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
