---
description: Annotate an image with overlay strokes that visually explain the answer to a visual-reasoning question. Use whenever the user asks to sketch on, draw on, mark up, trace, highlight, or visually explain something on an image.
---

# Annotate an image

When the user wants a vision model to *draw on* an image while answering a
question about it (mazes, diagrams, screenshots, photos, charts), call the
`sketch_annotate_inline` tool from the `sketchvlm` MCP server.

## When to use this

Triggers include phrases like:
- "annotate this image"
- "trace the path"
- "sketch the trajectory"
- "mark where X is"
- "highlight the buttons to click"
- "draw on this and explain"
- "show me visually how to..."

## How to call it

The user will provide an image path and a question. Pass both directly:

```
sketch_annotate_inline(
  image_path="<path the user gave>",
  question="<the user's question, paraphrased clearly>"
)
```

The tool returns the text answer plus the annotated PNG inline so the user
sees both in the chat. If the user asks to save the file (or to a specific
folder), use `sketch_annotate` instead and report the saved paths.

## Tips

- If the image path is relative, resolve it against the current working
  directory before calling.
- Default model is `claude-opus-4-5`. The user may override with phrases
  like "use sonnet" → `claude-sonnet-4-5` or "use haiku" → `claude-haiku-4-5`.
- If the model returns no strokes (parser warnings show up in the
  `sketch_annotate` response), pass back the answer text alone and note
  that no annotations were generated.
