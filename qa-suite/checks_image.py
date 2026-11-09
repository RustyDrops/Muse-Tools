"""Image checker: Pillow-script layout + rendered-PNG gates.

Layout reuse (import by path, never copied):
  layout-tools/qa_tools.py        -> check_layout
  layout-tools/delegate_qa_orchestrator.py -> extract_layout
  pillow-templates/qa.py                          -> blank-image stddev floor
Contrast thresholds re-implemented as constants citing the Node source
(engine/shared/design-quality.js): 4.5:1 body, 3:1 large text.
The type floor (title >= 34, body >= 28) is asserted here AND in tests:
a checker must NEVER pass by shrinking type.
"""

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

REUSE_LAYOUT_DIR = "/path/to/your/layout-tools"  # set to the directory holding qa_tools.py and the layout extractor
if REUSE_LAYOUT_DIR not in sys.path:
    sys.path.insert(0, REUSE_LAYOUT_DIR)

# Thresholds from engine/shared/design-quality.js (assessDesignQuality):
# body text warns below 4.5:1, large text below 3:1.
BODY_CONTRAST_MIN = 4.5
LARGE_CONTRAST_MIN = 3.0
# Blank-image floor from pillow-templates/qa.py (pixel stddev of L channel).
BLANK_STDDEV_FLOOR = 5.0
# Type floor: mirrors qa_tools.check_layout defaults; re-asserted here.
MIN_TITLE_SIZE = 34
MIN_BODY_SIZE = 28


def _luminance(rgb):
    def lin(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast_ratio(fg_hex, bg_hex):
    """WCAG contrast ratio between two #rrggbb colors."""
    def parse(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    l1 = _luminance(parse(fg_hex))
    l2 = _luminance(parse(bg_hex))
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def check_contrast(fg_hex, bg_hex, size_class="body"):
    """Contrast gate for one fg/bg pair. size_class: body|large."""
    floor = LARGE_CONTRAST_MIN if size_class == "large" else BODY_CONTRAST_MIN
    ratio = contrast_ratio(fg_hex, bg_hex)
    ok = ratio >= floor
    return {"pass": ok, "ratio": round(ratio, 2), "floor": floor,
            "size_class": size_class, "fg": fg_hex, "bg": bg_hex,
            "reason": "" if ok else (
                f"contrast {ratio:.2f}:1 < {floor}:1 floor "
                f"({size_class} text; {fg_hex} on {bg_hex})")}


def check_image_script(path):
    """Layout check of a Pillow generator script via the reused extractor.

    Returns verdict dict; {"error": ...} on extractor failure (exit 2
    upstream, never a delegate round). Re-asserts the type floor explicitly.
    """
    try:
        import delegate_qa_orchestrator as orch
        from qa_tools import check_layout
    except Exception as exc:
        return {"pass": False, "error": f"reuse import failed: {exc}",
                "failures": []}
    layout = orch.extract_layout(path)
    if "error" in layout:
        return {"pass": False, "error": layout["error"], "failures": []}
    result = json.loads(check_layout(**layout))
    failures = []
    if result["title_size"] < MIN_TITLE_SIZE or \
            result["body_size"] < MIN_BODY_SIZE:
        failures.append({
            "kind": "type-floor",
            "reason": (f"type below floor: title {result['title_size']}px "
                       f"(min {MIN_TITLE_SIZE}), body {result['body_size']}px "
                       f"(min {MIN_BODY_SIZE}) -- restore, never pass"),
            "title_size_px": result["title_size"],
            "body_size_px": result["body_size"]})
    for c in result.get("cards", []):
        if not c.get("title_fits"):
            failures.append({
                "kind": "title-overflow", "card": c["card"],
                "reason": (f"card {c['card']} title '{c['title']}' "
                           f"{c['title_width_px']}px wide, margin "
                           f"{c['title_margin_px']}px (< 20px)"),
                "title_width_px": c["title_width_px"],
                "title_margin_px": c["title_margin_px"]})
        if not c.get("body_fits"):
            failures.append({
                "kind": "body-overflow", "card": c["card"],
                "reason": (f"card {c['card']} body {c['body_height_px']}px "
                           f"in {c['body_lines']} lines, bottom margin "
                           f"{c['body_bottom_margin_px']}px (< 15px)"),
                "body_height_px": c["body_height_px"],
                "body_lines": c["body_lines"],
                "body_bottom_margin_px": c["body_bottom_margin_px"]})
    if not result.get("footer_fits"):
        failures.append({
            "kind": "footer-overflow",
            "reason": (f"footer bottom {result['footer_bottom_px']}px "
                       "exceeds canvas"),
            "footer_bottom_px": result["footer_bottom_px"]})
    return {"pass": result["pass"], "failures": failures,
            "measurements": result, "layout": layout}


def check_rendered_png(path, width=None, height=None):
    """Size/format/blank gates for a rendered PNG (pillow-templates/qa.py)."""
    try:
        from PIL import Image, ImageStat
    except Exception as exc:
        return {"pass": False, "error": f"PIL unavailable: {exc}",
                "failures": []}
    p = Path(path)
    if not p.exists():
        return {"pass": False, "error": f"target not found: {path}",
                "failures": []}
    failures, measurements = [], {}
    try:
        im = Image.open(p)
        im.load()
    except Exception as exc:
        return {"pass": False, "error": f"cannot open image: {exc}",
                "failures": []}
    measurements["size"] = list(im.size)
    measurements["mode"] = im.mode
    measurements["format"] = im.format
    if width is not None and height is not None:
        if tuple(im.size) != (width, height):
            failures.append({
                "kind": "dimensions",
                "reason": (f"size {tuple(im.size)}, expected "
                           f"({width}, {height})"),
                "size_px": list(im.size),
                "expected_px": [width, height]})
    gray = im.convert("L")
    stddev = ImageStat.Stat(gray).stddev[0]
    measurements["stddev"] = round(stddev, 2)
    if stddev < BLANK_STDDEV_FLOOR:
        failures.append({
            "kind": "blank",
            "reason": (f"image looks blank (stddev {stddev:.1f} < "
                       f"{BLANK_STDDEV_FLOOR})"),
            "stddev": round(stddev, 2)})
    return {"pass": not failures, "failures": failures,
            "measurements": measurements}
