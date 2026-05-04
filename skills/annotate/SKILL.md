---
description: Annotate an image with overlay strokes that visually explain the answer to a visual-reasoning question. Use whenever the user asks to sketch on, draw on, mark up, trace, highlight, or visually explain something on an image.
---

# Annotate an image

When the user wants to *draw on* an image while answering a question about
it (mazes, diagrams, screenshots, photos, charts), use this workflow. You do
the vision and the stroke planning yourself — the MCP tools only handle the
deterministic grid overlay and SVG rendering.

## Trigger phrases

- "annotate this image"
- "trace the path"
- "sketch the trajectory"
- "mark where X is"
- "circle the differences"
- "highlight the buttons to click"
- "draw on this and explain"

## Workflow

**Always preview before committing.** Vision models drift several percent of
image dimensions when estimating coordinates; the only reliable way to catch
misalignment is to render, look, and iterate. Plan on 2-3 preview rounds for
non-trivial images.

### Step 1 — Prepare

```
prepare_image(image_path="<the image path>")
```

For dense scenes, set `target_cols=80, target_rows=80`. For very large images
where grid labels may not survive viewer downscaling, set `scale=2`. The
default origin is `top_left` (matches how raster images read); pass
`origin="bottom_left"` only if the user explicitly wants math convention.

Save the returned `gridded_image_path`, `original_image_path`,
`original_pixel_w`, `original_pixel_h`, `grid_cols`, `grid_rows`, `origin`,
and read the `stroke_format_spec` carefully.

### Step 2 — Look

Use the built-in `Read` tool on `gridded_image_path`. You will see the image
with a labeled coordinate grid (left + bottom margins, light tick lines every
unit, labels every 5 units). Use those coordinates when planning strokes.

### Step 3 — Plan strokes

Write your strokes in the format from `stroke_format_spec`. Available stroke
types: `LINE`, `CURVE`, `ARROW`, `RECT`, `CIRCLE`, `ELLIPSE`, `TEXT`.

Pick the right primitive for the job:
- "trace a path" → `CURVE` (3+ waypoints) or `LINE` (single segment)
- "point to" / "mark this object" → `ARROW` or `CIRCLE`
- "circle the differences" → `CIRCLE` or `ELLIPSE` (not `RECT` — circles read more
  naturally for spot-the-difference style tasks)
- "outline a region" → `RECT` for axis-aligned features, `ELLIPSE` for organic ones
- Always add `TEXT` labels for non-obvious markings

**If you computed coordinates algorithmically** (BFS through a maze, OpenCV
contour detection, NumPy diff), use the `pxN,pyN` pixel format directly —
don't down-quantize to grid coords. Example:
```
<s1 type="CURVE" color="#ff3b30" width="4">px120,py340 px245,py280 px380,py215</s1>
```

### Step 4 — Preview

```
render_strokes(
  original_image_path="<from step 1>",
  strokes_xml="<your full XML>",
  grid_cols=<from step 1>,
  grid_rows=<from step 1>,
  origin="<from step 1>",
  preview=True
)
```

Then `Read` the returned `annotated_png_path`. Check:
- Are arrows/lines hitting the actual feature, or sliding off?
- Are circles centered on the right object?
- Are labels readable and not overlapping?

If alignment is off: revise the strokes (often nudging by 1-2 grid units is
enough) and call `render_strokes(..., preview=True)` again. Iterate until the
overlay is honest about what it's marking.

### Step 5 — Finalize

When the preview looks right:

```
render_strokes(
  ...,
  preview=False
)
```

`Read` the final `annotated_png_path` so it renders inline for the user, then
state your answer clearly. If `warnings` is non-empty, mention any strokes
that were skipped.

## Tips

- For UI screenshots with a header band, ignore the band when reading y
  coordinates — anchor to the actual content area, not pixel 0.
- If the user wants a specific color scheme ("use red for X, blue for Y"),
  honor it. Otherwise default to high-contrast colors that read against the
  background.
- Reuse the same `original_image_path` across iterations; only the
  `strokes_xml` changes.
- If the user wants to save outputs to a specific folder, pass
  `save_dir="<path>"` to either tool.
- Keep stroke counts low. Three precise strokes beat ten cluttered ones.
