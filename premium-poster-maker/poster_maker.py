#!/usr/bin/env python3
"""Premium Poster Maker - code-drawn poster transforms, no AI generation.

Takes a real photo and recreates the "premium poster" look with Pillow only:
a style grade, a legibility gradient behind the title, an inset border, and
EXACT text drawn from the strings you pass in. Text can never be mangled,
the animal/product is never re-rendered, and every run is reproducible.

Muse's job (the "with your help" part): pick the style, pick the focus point
so the subject is not cropped badly, set title/subtitle, run, VIEW the output,
adjust --focus-y / --top-fade / --grade and re-run. Deterministic, $0.

Styles: dark (cinematic, gold), bright (editorial, cream), bw (fine art),
vintage (sepia heirloom with title banner).

Usage:
  python3 poster_maker.py photo.jpg out.png --style dark \
      --title "RUSTY JORDAN STUDIOS" --subtitle "Pet Keepsakes" \
      --focus-y 0.62
"""
import argparse, sys
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

W, H = 1600, 2000  # 4:5 poster

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/noto/NotoSerifDisplay-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSerif-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
]
FONT_ITALIC_CANDIDATES = [
    "/usr/share/fonts/truetype/noto/NotoSerifDisplay-Italic.ttf",
    "/usr/share/fonts/truetype/noto/NotoSerif-Italic.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf",
]

def load_font(size, italic=False, path=None):
    cands = [path] if path else (FONT_ITALIC_CANDIDATES if italic else FONT_CANDIDATES)
    for c in cands:
        if not c:
            continue
        try:
            return ImageFont.truetype(c, size)
        except Exception:
            pass
    return ImageFont.load_default()

def crop_focus(img, focus_x, focus_y, out_w=None, out_h=None):
    """Crop around the focus point (0..1) to the output aspect, then resize."""
    out_w, out_h = out_w or W, out_h or H
    img = ImageOps.exif_transpose(img).convert("RGB")
    w, h = img.size
    target = out_w / out_h
    if w / h > target:  # too wide
        cw, ch = int(h * target), h
    else:
        cw, ch = w, int(w / target)
    cx, cy = int(focus_x * w), int(focus_y * h)
    x0 = min(max(cx - cw // 2, 0), w - cw)
    y0 = min(max(cy - ch // 2, 0), h - ch)
    return img.crop((x0, y0, x0 + cw, y0 + ch)).resize((out_w, out_h), Image.LANCZOS)

def gradient_overlay(img, top_rgba, height_frac=0.42):
    """Vertical gradient from top_rgba at the top fading to transparent."""
    grad = Image.new("L", (1, int(H * height_frac)))
    for y in range(grad.height):
        grad.putpixel((0, y), int(top_rgba[3] * (1 - y / grad.height) ** 1.5))
    grad = grad.resize((W, grad.height))
    layer = Image.new("RGBA", (W, grad.height), top_rgba[:3] + (0,))
    layer.putalpha(grad)
    out = img.convert("RGBA")
    out.alpha_composite(layer, (0, 0))
    return out

def vignette(img, strength=0.35):
    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask)
    d.ellipse((-W * 0.25, -H * 0.25, W * 1.25, H * 1.25), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(180))
    black = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    out = Image.composite(img, black, mask.point(lambda p: int(255 - (255 - p) * strength)))
    return out.convert("RGBA")

def sepia(img):
    gray = ImageOps.grayscale(img).convert("L")
    out = ImageOps.colorize(gray, black=(43, 30, 18), mid=(133, 102, 68), white=(245, 234, 210))
    return out.convert("RGBA")

def tracked_text(draw, cx, y, text, font, fill, tracking=10):
    """Draw letter-spaced centred text; returns its height."""
    widths = [draw.textlength(ch, font=font) for ch in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x = cx - total / 2
    for ch, wch in zip(text, widths):
        draw.text((x, y), ch, font=font, fill=fill)
        x += wch + tracking
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[3] - bbox[1]

def fit_font(draw, text, max_width, start, italic=False, path=None, tracking=10):
    size = start
    while size > 20:
        f = load_font(size, italic=italic, path=path)
        w = sum(draw.textlength(ch, font=f) for ch in text) + tracking * (len(text) - 1)
        if w <= max_width:
            return f
        size -= 4
    return load_font(20, italic=italic, path=path)

BAND_H = 320
BAND_COLORS = {"dark": (18, 24, 20), "bright": (250, 247, 240), "bw": (10, 10, 10), "vintage": (74, 54, 36)}

def make(photo, style, title, subtitle, focus_x, focus_y, font_path, band=False):
    if band:
        photo_img = crop_focus(Image.open(photo), focus_x, focus_y, W, H - BAND_H)
        canvas = Image.new("RGB", (W, H), BAND_COLORS.get(style, (18, 24, 20)))
        canvas.paste(photo_img, (0, BAND_H))
        img = canvas
    else:
        img = crop_focus(Image.open(photo), focus_x, focus_y)
    draw_tmp = ImageDraw.Draw(img)
    title_font = fit_font(draw_tmp, title, W - 260, 92, path=font_path)
    sub_font = load_font(54, italic=True, path=font_path)

    if style == "dark":
        img = ImageEnhance.Color(img).enhance(0.88)
        img = ImageEnhance.Contrast(img).enhance(1.08)
        img = ImageEnhance.Brightness(img).enhance(0.94).convert("RGBA")
        img = gradient_overlay(img, (12, 18, 14, 215))
        img = vignette(img, 0.30)
        d = ImageDraw.Draw(img)
        d.rectangle((36, 36, W - 36, H - 36), outline=(198, 168, 110, 255), width=3)
        ty = 92 if band else 150
        th = tracked_text(d, W // 2, ty, title, title_font, (216, 184, 120, 255))
        if subtitle:
            tracked_text(d, W // 2, ty + th + 30, subtitle, sub_font, (226, 205, 160, 255), tracking=4)
    elif style == "bright":
        img = ImageEnhance.Brightness(img).enhance(1.06)
        img = ImageEnhance.Color(img).enhance(0.94).convert("RGBA")
        img = gradient_overlay(img, (250, 247, 240, 255), height_frac=0.40)
        d = ImageDraw.Draw(img)
        ty = 92 if band else 130
        th = tracked_text(d, W // 2, ty, title, title_font, (38, 38, 40, 255))
        if subtitle:
            tracked_text(d, W // 2, ty + th + 30, subtitle, sub_font, (70, 70, 72, 255), tracking=4)
    elif style == "bw":
        img = ImageOps.grayscale(img)
        img = ImageEnhance.Contrast(img).enhance(1.12).convert("RGBA")
        img = gradient_overlay(img, (0, 0, 0, 200))
        d = ImageDraw.Draw(img)
        d.rectangle((36, 36, W - 36, H - 36), outline=(255, 255, 255, 255), width=4)
        ty = 92 if band else 140
        th = tracked_text(d, W // 2, ty, title, title_font, (255, 255, 255, 255))
        if subtitle:
            tracked_text(d, W // 2, ty + th + 30, subtitle, sub_font, (240, 240, 240, 255), tracking=4)
    elif style == "vintage":
        img = sepia(img)
        img = ImageEnhance.Contrast(img).enhance(1.03)
        img = vignette(img, 0.28)
        d = ImageDraw.Draw(img)
        banner_h = 250
        d.rectangle((0, 0, W, banner_h), fill=(74, 54, 36, 255))
        th = tracked_text(d, W // 2, 52, title, title_font, (245, 234, 210, 255))
        if subtitle:
            tracked_text(d, W // 2, 52 + th + 22, subtitle, sub_font, (238, 222, 192, 255), tracking=4)
        d.rectangle((24, 24, W - 24, H - 24), outline=(245, 234, 210, 255), width=3)
    else:
        sys.exit(f"unknown style: {style}")
    return img.convert("RGB")

def main():
    ap = argparse.ArgumentParser(description="Code-drawn premium poster maker (no AI).")
    ap.add_argument("photo")
    ap.add_argument("output")
    ap.add_argument("--style", default="dark", choices=["dark", "bright", "bw", "vintage"])
    ap.add_argument("--title", default="")
    ap.add_argument("--subtitle", default="")
    ap.add_argument("--focus-x", type=float, default=0.5, help="subject centre, 0..1")
    ap.add_argument("--focus-y", type=float, default=0.55, help="subject centre, 0..1")
    ap.add_argument("--font", default=None, help="path to a serif TTF for title/subtitle")
    ap.add_argument("--band", action="store_true", help="put the title in a solid band above the photo (use when the subject head is near the top)")
    a = ap.parse_args()
    out = make(a.photo, a.style, a.title, a.subtitle, a.focus_x, a.focus_y, a.font, a.band)
    out.save(a.output)
    print(f"wrote {a.output} style={a.style} title={a.title!r}")

if __name__ == "__main__":
    main()
