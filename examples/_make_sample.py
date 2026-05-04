"""Generate the sample maze used by the README example.

Re-run this if you want to refresh `examples/maze.png`. Output is fully
deterministic (no randomness) so the committed PNG matches what this script
would produce on any machine.
"""

import pathlib

from PIL import Image, ImageDraw


def make_maze(path: pathlib.Path) -> None:
    cell = 40
    cols, rows = 12, 10
    margin = 20
    w = cols * cell + 2 * margin
    h = rows * cell + 2 * margin

    img = Image.new("RGB", (w, h), (245, 245, 245))
    d = ImageDraw.Draw(img)

    walls = [
        # outer border
        ((0, 0), (cols, 0)),
        ((0, 0), (0, rows)),
        ((cols, 0), (cols, rows)),
        ((0, rows), (cols, rows)),
        # interior walls (a simple solvable layout)
        ((2, 0), (2, 6)),
        ((4, 2), (4, 8)),
        ((6, 0), (6, 5)),
        ((6, 7), (6, 10)),
        ((8, 2), (8, 9)),
        ((10, 0), (10, 6)),
        ((2, 6), (4, 6)),
        ((6, 5), (8, 5)),
        ((4, 8), (10, 8)),
    ]
    for (x0, y0), (x1, y1) in walls:
        d.line(
            [
                (margin + x0 * cell, margin + y0 * cell),
                (margin + x1 * cell, margin + y1 * cell),
            ],
            fill=(40, 40, 40),
            width=4,
        )

    sx, sy = margin + 1 * cell + cell // 2, margin + 0 * cell + cell // 2
    ex, ey = margin + (cols - 1) * cell + cell // 2, margin + (rows - 1) * cell + cell // 2
    d.ellipse([sx - 12, sy - 12, sx + 12, sy + 12], fill=(0, 150, 0))
    d.ellipse([ex - 12, ey - 12, ex + 12, ey + 12], fill=(200, 0, 0))
    d.text((sx - 18, sy - 6), "S", fill=(255, 255, 255))
    d.text((ex - 6, ey - 6), "E", fill=(255, 255, 255))

    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="PNG")


if __name__ == "__main__":
    out = pathlib.Path(__file__).resolve().parent / "maze.png"
    make_maze(out)
    print(f"wrote {out}")
