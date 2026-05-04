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
- "highlight the buttons to click"
- "draw on this and explain"
- "show me visually how to..."

## Workflow

1. **Prepare the image.** Call:
   ```
   prepare_image(image_path="<the image path>")
   ```
   Save the returned `gridded_image_path`, `original_image_path`, `grid_cols`,
   `grid_rows`, `origin`, and read the `stroke_format_spec`.

2. **Look at the gridded image.** Use the built-in `Read` tool on
   `gridded_image_path`. You will see the original image with a labeled
   coordinate grid (left + bottom margins). Use those grid coordinates when
   planning strokes — `xNyM` tokens map directly to the visible labels.

3. **Plan and write your strokes** in the format from `stroke_format_spec`.
   Output one or more `<sN type="...">` tags followed by `<answer>...</answer>`.
   Keep strokes minimal and meaningful — one or two clean curves usually beats
   ten cluttered ones. Pick high-contrast colors that read against the image.

4. **Render the strokes.** Call:
   ```
   render_strokes(
     original_image_path="<from step 1>",
     strokes_xml="<your full stroke XML including the <answer> tag>",
     grid_cols=<from step 1>,
     grid_rows=<from step 1>,
     origin="<from step 1>"
   )
   ```

5. **Show the result.** Use the `Read` tool on the returned
   `annotated_png_path` so the annotated image renders inline, then state the
   answer to the user clearly. If `warnings` is non-empty, mention any strokes
   that were skipped.

## Tips

- If the user asks for a quick / cheap pass on a large image, start with a
  smaller grid: `prepare_image(image_path=..., target_cols=30, target_rows=30)`.
- For images where downward-positive y feels more natural (UI screenshots),
  pass `origin="top_left"` to `prepare_image` and to `render_strokes`.
- Reuse the same `original_image_path` across multiple `render_strokes` calls
  if the user wants to iterate (e.g. "make the arrow red instead").
- If the user wants to save outputs to a specific folder, pass
  `save_dir="<path>"` to either tool.
