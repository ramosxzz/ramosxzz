"""Convert avatar to ASCII art (run once, writes ascii.txt)."""
import sys
from pathlib import Path
from PIL import Image, ImageOps, ImageFilter

RAMP = " .'`,:;!|ijlkmw%"
DENSE = "@%M#&WmH8"  # textured fill for solid black areas
COLS, ROWS = int(sys.argv[1]) if len(sys.argv) > 1 else 40, int(sys.argv[2]) if len(sys.argv) > 2 else 25

here = Path(__file__).parent
img = Image.open(here / "avatar.jpg").convert("L")
img = img.crop((20, 0, 440, 460))
img = ImageOps.autocontrast(img).filter(ImageFilter.EDGE_ENHANCE)
img = img.resize((COLS, ROWS), Image.LANCZOS)

lines = []
for y in range(ROWS):
    row = ""
    for x in range(COLS):
        darkness = 255 - img.getpixel((x, y))
        if darkness > 225:
            row += DENSE[(x * 7 + y * 13 + (x * y) % 5) % len(DENSE)]
        else:
            row += RAMP[min(len(RAMP) - 1, darkness * len(RAMP) // 226)]
    lines.append(row.rstrip())
(here.parent / "ascii.txt").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
