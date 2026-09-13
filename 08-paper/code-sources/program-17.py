from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
FIGDIR = ROOT / "06-figure" / "figures"
OUT = ROOT / "06-figure" / "official-figures-contact-sheet-20260913.png"

ids = [
    "FIG-Q1-C-FIELD", "FIG-Q1-END-EFFECT", "FIG-Q2-C-PROFILES", "FIG-Q2-MODEL-ABLATION",
    "FIG-Q2-GRID-CONV", "FIG-Q3-THRESHOLD-TRAJECTORY", "FIG-Q3-BRACKET-ZOOM",
    "FIG-Q3-SENS-ONEFACTOR", "FIG-Q4-RADIUS-TIME", "FIG-Q4-THRESHOLD-TRAJECTORY",
    "FIG-Q1-GRID-CONV", "FIG-Q3-SPACE-CONV", "FIG-Q4-SPACE-CONV",
]

W, H = 900, 620
sheet = Image.new("RGB", (W * 4, H * 4), "white")
draw = ImageDraw.Draw(sheet)
font = ImageFont.truetype("simhei.ttf", 28)
small = ImageFont.truetype("simhei.ttf", 22)

for i, fid in enumerate(ids):
    path = FIGDIR / f"{fid}.png"
    if not path.exists():
        raise FileNotFoundError(path)
    with Image.open(path) as src:
        src = src.convert("RGB")
        src.thumbnail((W - 40, H - 90), Image.Resampling.LANCZOS)
        x = (i % 4) * W
        y = (i // 4) * H
        draw.rectangle((x, y, x + W - 1, y + H - 1), outline=(190, 190, 190), width=2)
        draw.text((x + 18, y + 12), f"{i+1:02d}  {fid}", fill=(0, 0, 0), font=font)
        px = x + (W - src.width) // 2
        py = y + 62 + (H - 72 - src.height) // 2
        sheet.paste(src, (px, py))

sheet.save(OUT, dpi=(150, 150))
print(OUT)

