# fig08C_merge_panels.py
# Creates a single Q1-style integrated panel: (A) 10km render | (B) 5km render | (C) Fig 8B stats
# Outputs: fig08C_integrated.png (600 dpi) + fig08C_integrated.pdf

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(r"C:\projects\icvars-metaverse-pipeline-risk")
FIGDIR = ROOT / "paper" / "figures"

# Your confirmed files (edit only if names differ)
IMG_10 = FIGDIR / "fig08A_metaverse_render10km.png"
IMG_5  = FIGDIR / "fig08A_metaverse_render5km.png"

# Fig 8B (auto-pick newest matching if you have variants)
CANDS_8B = sorted(FIGDIR.glob("fig08B*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
if not CANDS_8B:
    raise FileNotFoundError(f"No fig08B*.png found in: {FIGDIR}")
IMG_8B = CANDS_8B[0]

OUT_PNG = FIGDIR / "fig08C_integrated.png"
OUT_PDF = FIGDIR / "fig08C_integrated.pdf"

DPI = 600

# Layout controls (in pixels)
GAP = 80                 # whitespace between panels
PAD = 120                # outer margin
HEADER_H = 170           # space for title row
LABEL_H = 90             # space for panel labels
BG = (255, 255, 255)

TITLE = "Fig. 8 — Resolution sensitivity and metaverse rendering (10km vs 5km)"
LABELS = [
    "A) 10km metaverse rendering (3D extrusion)",
    "B) 5km metaverse rendering (3D extrusion)",
    "C) Tail + stability summary (z-score sensitivity)"
]

def load_rgb(path: Path) -> Image.Image:
    if not path.exists():
        raise FileNotFoundError(f"Missing: {path}")
    im = Image.open(path).convert("RGB")
    return im

def try_font(size: int) -> ImageFont.FreeTypeFont:
    # Robust fallback across Windows
    for name in ["arial.ttf", "calibri.ttf", "segoeui.ttf"]:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()

def fit_to_height(im: Image.Image, target_h: int) -> Image.Image:
    w, h = im.size
    if h == target_h:
        return im
    new_w = int(round(w * (target_h / h)))
    return im.resize((new_w, target_h), resample=Image.LANCZOS)

def main():
    im10 = load_rgb(IMG_10)
    im5  = load_rgb(IMG_5)
    im8b = load_rgb(IMG_8B)

    # Make all panels same content height (use the 3D render height as anchor)
    target_h = im10.size[1]
    im5  = fit_to_height(im5, target_h)
    im8b = fit_to_height(im8b, target_h)

    # Compose final canvas
    w10, h = im10.size
    w5, _  = im5.size
    w8, _  = im8b.size

    total_w = PAD*2 + w10 + GAP + w5 + GAP + w8
    total_h = PAD*2 + HEADER_H + LABEL_H + h

    canvas = Image.new("RGB", (total_w, total_h), BG)
    draw = ImageDraw.Draw(canvas)

    font_title = try_font(56)
    font_label = try_font(40)

    # Title
    tx, ty = PAD, PAD
    draw.text((tx, ty), TITLE, fill=(0, 0, 0), font=font_title)

    # Panel top y
    y0 = PAD + HEADER_H + LABEL_H

    # X positions
    x10 = PAD
    x5  = x10 + w10 + GAP
    x8  = x5  + w5  + GAP

    # Panel labels
    ly = PAD + HEADER_H
    draw.text((x10, ly), LABELS[0], fill=(0, 0, 0), font=font_label)
    draw.text((x5,  ly), LABELS[1], fill=(0, 0, 0), font=font_label)
    draw.text((x8,  ly), LABELS[2], fill=(0, 0, 0), font=font_label)

    # Paste panels
    canvas.paste(im10, (x10, y0))
    canvas.paste(im5,  (x5,  y0))
    canvas.paste(im8b, (x8,  y0))

    # Optional thin separators (clean Q1 look)
    sep_color = (30, 30, 30)
    # vertical separators
    draw.line([(x10 + w10 + GAP//2, y0), (x10 + w10 + GAP//2, y0 + h)], fill=sep_color, width=3)
    draw.line([(x5  + w5  + GAP//2, y0), (x5  + w5  + GAP//2, y0 + h)], fill=sep_color, width=3)

    # Save PNG with DPI metadata
    canvas.save(OUT_PNG, dpi=(DPI, DPI))

    # Save PDF (single-page)
    canvas.save(OUT_PDF, "PDF", resolution=DPI)

    print("Inputs:")
    print("  10km:", IMG_10)
    print("   5km:", IMG_5)
    print("   8B :", IMG_8B)
    print("Saved:")
    print("  PNG:", OUT_PNG)
    print("  PDF:", OUT_PDF)

if __name__ == "__main__":
    main()