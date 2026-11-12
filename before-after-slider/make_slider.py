#!/usr/bin/env python3
"""Before/after slider viewer — the standard SocialForge comparison view.

Rusty, 2026-11-12: "make sure to use this in SocialForge. Great for
comparing changes in all sorts of ways."

Usage:
    python3 make_slider.py spec.json output.html

Spec JSON:
{
  "title": "Page title",
  "lede": "One line under the title (optional)",
  "note": "Small print at the bottom (optional)",
  "width": 760,            // optional, embedded image width
  "quality": 70,           // optional, embedded JPEG quality
  "pairs": [
    {"title": "Example 1 — Declutter",
     "sub": "What changed, in one line (optional)",
     "before": "/path/to/before.jpg",
     "after":  "/path/to/after.jpg"}
  ]
}

Output is ONE standalone HTML file: images are downscaled and
embedded as data URIs, the slider is a draggable wipe (pointer +
range input), BEFORE shows on the left of the line, AFTER on the
right. No dependencies, works in chat widgets and in a browser.

Use it for: Tier 2 cleanup offers and approvals, grouped-editor
compare, template redesign reviews, brand-guide option comparisons,
seasonal refresh old-vs-new, any original-vs-changed pair.
"""
import base64
import io
import json
import sys
from pathlib import Path

from PIL import Image

CSS = """
  * { box-sizing: border-box; }
  body { margin:0; padding:16px; font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
         background: var(--hatch-widget-bg, transparent); color: var(--hatch-widget-text, #1c1d18); }
  .wrap { max-width: 560px; margin: 0 auto; }
  h1 { font-size: 19px; margin: 0 0 2px; }
  .lede { font-size: 13.5px; opacity:.75; margin: 0 0 18px; }
  .pair { margin-bottom: 26px; }
  h2 { font-size: 15.5px; margin: 0 0 2px; }
  .sub { font-size: 13px; opacity:.75; margin: 0 0 8px; }
  .cmp { position: relative; width: 100%; overflow: hidden; border-radius: 12px;
          border: 1px solid var(--hatch-widget-border, rgba(120,120,120,.35));
          touch-action: none; cursor: ew-resize; user-select: none; -webkit-user-select: none; }
  .cmp img { display:block; width:100%; height:auto; pointer-events:none; }
  .cmp img.before { position:absolute; inset:0; height:100%; object-fit:cover;
                     clip-path: inset(0 calc(100% - var(--pos)) 0 0); }
  .handle { position:absolute; top:0; bottom:0; left: var(--pos); width:2px; margin-left:-1px;
             background:#fff; box-shadow: 0 0 0 1px rgba(0,0,0,.35), 0 0 12px rgba(0,0,0,.35); }
  .grip { position:absolute; top:50%; left:50%; transform: translate(-50%,-50%);
           width:38px; height:38px; border-radius:50%; background:#fff; color:#333;
           display:flex; align-items:center; justify-content:center; font-size:19px; font-weight:700;
           box-shadow: 0 1px 6px rgba(0,0,0,.45); letter-spacing:-2px; padding-right:2px; }
  .tag { position:absolute; top:8px; font-size:10.5px; font-weight:700; letter-spacing:.08em;
          padding:3px 8px; border-radius:999px; background:rgba(0,0,0,.55); color:#fff; }
  .tag-before { left:8px; } .tag-after { right:8px; }
  .range { width:100%; margin-top:8px; accent-color: #c8871a; }
  .note { font-size: 12.5px; opacity:.7; margin-top: 2px; }
"""

JS = """
  document.querySelectorAll('.cmp').forEach(function(cmp) {
    var range = cmp.parentElement.querySelector('.range');
    function setPos(clientX) {
      var r = cmp.getBoundingClientRect();
      var pct = (clientX - r.left) / r.width * 100;
      pct = Math.max(0, Math.min(100, pct));
      cmp.style.setProperty('--pos', pct + '%');
      if (range) range.value = pct;
    }
    var dragging = false;
    cmp.addEventListener('pointerdown', function(e) { dragging = true; cmp.setPointerCapture(e.pointerId); setPos(e.clientX); });
    cmp.addEventListener('pointermove', function(e) { if (dragging) setPos(e.clientX); });
    cmp.addEventListener('pointerup', function() { dragging = false; });
    cmp.addEventListener('pointercancel', function() { dragging = false; });
    if (range) range.addEventListener('input', function() { cmp.style.setProperty('--pos', range.value + '%'); });
  });
"""


def embed(path, width, quality):
    im = Image.open(path).convert("RGB")
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=quality)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def slider_html(pair, width, quality):
    before = embed(pair["before"], width, quality)
    after = embed(pair["after"], width, quality)
    title = pair.get("title", "Before / after")
    sub = pair.get("sub", "")
    sub_html = f'<p class="sub">{sub}</p>' if sub else ""
    return f"""
  <section class="pair">
    <h2>{title}</h2>
    {sub_html}
    <div class="cmp" style="--pos:50%">
      <img class="after" src="{after}" alt="{title} — after">
      <img class="before" src="{before}" alt="{title} — before">
      <span class="tag tag-before">BEFORE</span>
      <span class="tag tag-after">AFTER</span>
      <div class="handle"><div class="grip">&#8249;&#8250;</div></div>
    </div>
    <input class="range" type="range" min="0" max="100" value="50" aria-label="Reveal changed image">
  </section>"""


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    width = int(spec.get("width", 760))
    quality = int(spec.get("quality", 70))
    pairs = "\n".join(slider_html(p, width, quality) for p in spec["pairs"])
    lede = spec.get("lede", "Drag the line (or the slider under each photo) to compare the original with the changed version.")
    note = spec.get("note", "")
    note_html = f'<p class="note">{note}</p>' if note else ""
    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{spec.get('title', 'Before / after')}</title>
<style>{CSS}</style></head>
<body><div class="wrap">
  <h1>{spec.get('title', 'Before / after')}</h1>
  <p class="lede">{lede}</p>
{pairs}
  {note_html}
</div>
<script>{JS}</script>
</body></html>"""
    out = Path(sys.argv[2])
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out} ({len(html)} bytes, {len(spec['pairs'])} pair(s))")


if __name__ == "__main__":
    main()
