"""Rendered-slide PNG checks: centre offset, edge clip, blank floor.

Rendered PNG in, verdict out. No PowerPoint/Google Slides parsing, no
aesthetic judgement, no real decks as fixtures (synthetic only).

Reuses BLANK_STDDEV_FLOOR from checks_image (the pillow-templates/qa.py
blank-image floor); the rendered-PNG gate shape ({"pass", "failures",
"measurements"} with optional {"error"}) and the qa_suite.py exit-code
contract (0 PASS / 1 FAIL / 2 checker-error) are preserved.

Method:
  background  = most common of the four corner pixels (opaque RGB).
  content     = pixels whose max channel distance from background exceeds
                BG_TOLERANCE; the content bbox is their bounding box.
  centre      = bbox centre vs frame centre; offset reported in px.
  edge clip   = content pixels touching a frame edge; an edge with at
                least EDGE_TOUCH_MIN_PX such pixels is a text-loss risk.
"""

from pathlib import Path

from checks_image import BLANK_STDDEV_FLOOR

# Judgement call: max allowed content-bbox centre offset in px for a
# 1280x720 slide (~3.75% of frame width). Recalibration is a data change:
# edit this constant; fixture measurements live in test_checks_slide.py.
CENTRE_OFFSET_MAX_PX = 48.0
# Per-channel distance from the corner-sampled background that counts as
# content. 12 tolerates JPEG ringing / anti-aliased edges on flat fills.
BG_TOLERANCE = 12
# Minimum content pixels touching one frame edge before it counts as a
# clip (rules out single anti-aliased dots in the corner sample).
EDGE_TOUCH_MIN_PX = 8


def _background(px, w, h):
    corners = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]
    return max(set(corners), key=corners.count)


def _is_content(pixel, bg):
    return max(abs(a - b) for a, b in zip(pixel, bg)) > BG_TOLERANCE


def check_slide_png(path):
    """Centre-offset / edge-clip / blank gates for a rendered slide PNG."""
    try:
        from PIL import Image, ImageStat
    except Exception as exc:
        return {"pass": False, "error": f"PIL unavailable: {exc}",
                "failures": []}
    p = Path(path)
    if not p.exists():
        return {"pass": False, "error": f"target not found: {path}",
                "failures": []}
    if p.suffix.lower() not in (".png", ".jpg", ".jpeg"):
        return {"pass": False,
                "error": f"slide check needs .png/.jpg, got '{p.suffix}'",
                "failures": []}
    try:
        im = Image.open(p)
        im.load()
    except Exception as exc:
        return {"pass": False, "error": f"cannot open image: {exc}",
                "failures": []}
    rgb = im.convert("RGB")
    w, h = rgb.size
    measurements = {"size": [w, h], "mode": im.mode, "format": im.format}

    stddev = ImageStat.Stat(im.convert("L")).stddev[0]
    measurements["stddev"] = round(stddev, 2)
    measurements["blank_floor"] = BLANK_STDDEV_FLOOR
    failures = []
    if stddev < BLANK_STDDEV_FLOOR:
        failures.append({
            "kind": "blank",
            "reason": (f"slide looks blank (stddev {stddev:.1f} < "
                       f"{BLANK_STDDEV_FLOOR})"),
            "stddev": round(stddev, 2)})
        return {"pass": False, "failures": failures,
                "measurements": measurements}

    px = rgb.load()
    bg = _background(px, w, h)
    measurements["background_rgb"] = list(bg)
    xs, ys = [], []
    top = bottom = left = right = 0
    for y in range(h):
        for x in range(w):
            if not _is_content(px[x, y], bg):
                continue
            xs.append(x)
            ys.append(y)
            if y == 0:
                top += 1
            if y == h - 1:
                bottom += 1
            if x == 0:
                left += 1
            if x == w - 1:
                right += 1
    if not xs:
        failures.append({
            "kind": "blank",
            "reason": "no content pixels found against sampled background",
            "stddev": round(stddev, 2)})
        return {"pass": False, "failures": failures,
                "measurements": measurements}

    bbox = [min(xs), min(ys), max(xs), max(ys)]
    measurements["content_bbox"] = bbox
    cx, cy = (bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0
    fx, fy = w / 2.0, h / 2.0
    dx, dy = cx - fx, cy - fy
    dist = (dx * dx + dy * dy) ** 0.5
    measurements["content_centre_xy"] = [round(cx, 1), round(cy, 1)]
    measurements["frame_centre_xy"] = [fx, fy]
    measurements["centre_offset_px"] = {
        "dx": round(dx, 1), "dy": round(dy, 1),
        "distance": round(dist, 1)}
    measurements["centre_offset_max_px"] = CENTRE_OFFSET_MAX_PX
    if dist > CENTRE_OFFSET_MAX_PX:
        failures.append({
            "kind": "off-centre",
            "reason": (f"content centre off frame centre by {dist:.1f}px "
                       f"(dx {dx:+.1f}, dy {dy:+.1f}; max "
                       f"{CENTRE_OFFSET_MAX_PX}px)"),
            "centre_offset_px": round(dist, 1),
            "dx_px": round(dx, 1), "dy_px": round(dy, 1)})

    edge_counts = {"top": top, "bottom": bottom,
                   "left": left, "right": right}
    measurements["edge_touch_px"] = edge_counts
    for edge, count in edge_counts.items():
        if count >= EDGE_TOUCH_MIN_PX:
            failures.append({
                "kind": "edge-clip",
                "reason": (f"{count}px of content touch the {edge} frame "
                           f"edge (>= {EDGE_TOUCH_MIN_PX}px: clip/text-loss "
                           f"risk)"),
                "edge": edge, "touch_px": count})

    return {"pass": not failures, "failures": failures,
            "measurements": measurements}
