"""Convert avatar to ASCII art (run once, writes ascii.txt).

Usage: python tools/make_ascii.py [cols] [rows]
"""
import sys
from pathlib import Path
from PIL import Image, ImageOps, ImageFilter, ImageDraw

RAMP = " .:-=+*#%@"
CROP = (60, 0, 420, 380)  # tight on head and shoulders
COLS = int(sys.argv[1]) if len(sys.argv) > 1 else 76
ROWS = int(sys.argv[2]) if len(sys.argv) > 2 else 48

here = Path(__file__).parent
img = Image.open(here / "avatar.jpg").convert("L").crop(CROP)
img = ImageOps.autocontrast(img, cutoff=1)

# blank out the white background (flood fill from the top corners)
mask = img.point(lambda v: 255 if v > 215 else 0)
for seed in [(0, 0), (mask.width - 1, 0)]:
    if mask.getpixel(seed) == 255:
        ImageDraw.floodfill(mask, seed, 128)
img.paste(255, mask=mask.point(lambda v: 255 if v == 128 else 0).filter(ImageFilter.MaxFilter(3)))

img = img.resize((COLS, ROWS), Image.LANCZOS)
lines = []
for y in range(ROWS):
    row = "".join(RAMP[(255 - img.getpixel((x, y))) * len(RAMP) // 256] for x in range(COLS))
    lines.append(row.rstrip())
(here.parent / "ascii.txt").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
