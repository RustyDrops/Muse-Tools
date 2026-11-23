#!/usr/bin/env python3
"""Post graphic maker — bold 1080x1080 cards, code-drawn with Pillow.

Usage:
    python3 make_post_graphic.py cards.json [out_dir]

cards.json is a list of card objects:
    {
      "bg": [11, 32, 72],            # background RGB
      "accent": [252, 61, 33],       # kicker + pill + top band RGB
      "kicker": "NASA Design Challenge  •  Grades 6–8",
      "title": ["Design the", "Airport of", "the Future"],
      "title_size": 118,             # optional, default 112
      "sub": "One short sentence or two about the post.",
      "pill": "REGISTER BY DEC 8, 2026",
      "footer": "STEMpact",
      "footer_sub": "STEM resources for middle schoolers",
      "out": "post-1.png"
    }

Layout note: the pill flows BELOW the sub text wherever it ends. A fixed
pill position overlaps the last sub line whenever the sub wraps to 3 lines
(learned the hard way, 2026-11-22). Always view the renders before use.
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1080
FONT_CANDIDATES_BOLD = [
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
FONT_CANDIDATES_REG = [
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def pick_font(candidates, size):
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    raise FileNotFoundError(f"no font found in {candidates}")


def wrap(draw, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if draw.textlength(t, font=fnt) <= max_w:
            cur = t
        else:
            lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    return lines


def pill(draw, cx, y, text, fnt, fill, txt_fill):
    tw = draw.textlength(text, font=fnt)
    pad_x, pad_y = 36, 18
    box = [cx - tw / 2 - pad_x, y, cx + tw / 2 + pad_x, y + fnt.size + pad_y * 2]
    draw.rounded_rectangle(box, radius=(box[3] - box[1]) // 2, fill=fill)
    draw.text((cx, y + pad_y - 4), text, font=fnt, fill=txt_fill, anchor="ma")
    return box[3]


def card(spec, out_dir):
    bg = tuple(spec["bg"])
    accent = tuple(spec["accent"])
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 26], fill=accent)
    for r, a in [(300, 40), (210, 60), (130, 85)]:
        d.ellipse([W - r + 120, H - r + 140, W + r + 120, H + r + 140],
                  fill=tuple(min(255, c + a) for c in bg))
    kf = pick_font(FONT_CANDIDATES_BOLD, 40)
    d.text((80, 92), spec["kicker"].upper(), font=kf, fill=accent)
    title_size = spec.get("title_size", 112)
    tf = pick_font(FONT_CANDIDATES_BOLD, title_size)
    y = 190
    for line in spec["title"]:
        d.text((80, y), line, font=tf, fill=(255, 255, 255))
        y += int(title_size * 1.18)
    sf = pick_font(FONT_CANDIDATES_REG, 44)
    y += 26
    for line in wrap(d, spec["sub"], sf, W - 160):
        d.text((80, y), line, font=sf, fill=(235, 240, 248))
        y += 58
    pf = pick_font(FONT_CANDIDATES_BOLD, 46)
    pill(d, W // 2, y + 36, spec["pill"], pf, accent, (255, 255, 255))
    ff = pick_font(FONT_CANDIDATES_BOLD, 42)
    d.text((W // 2, H - 130), spec["footer"], font=ff,
           fill=(255, 255, 255), anchor="ma")
    sf2 = pick_font(FONT_CANDIDATES_REG, 30)
    d.text((W // 2, H - 74), spec["footer_sub"], font=sf2,
           fill=(200, 210, 225), anchor="ma")
    path = os.path.join(out_dir, spec["out"])
    img.save(path, "PNG")
    print(path)


def main():
    cards_file = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "."
    os.makedirs(out_dir, exist_ok=True)
    with open(cards_file) as f:
        specs = json.load(f)
    for spec in specs:
        card(spec, out_dir)


if __name__ == "__main__":
    main()
