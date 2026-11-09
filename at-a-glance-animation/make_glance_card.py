#!/usr/bin/env python3
"""Populate a reusable at-a-glance card.

Usage:
  python3 make_glance_card.py --header "Thursday PM showers" \
    --subheader "PM showers, high 74°F, 40% rain — no alert issued" \
    --details "Showers from about 3 p.m., 40% at 4 p.m. Night showers late, low 48°F. Forecast checked this morning; it can still move." \
    --link "https://weather.com/" --link-label "Forecast ›" \
    --icon rain --output cards/thursday-pm-showers-2026-11-05.html

Writes a small standalone HTML fragment (no doctype/html/head/body) ready
for widget.create_html_file_widget. One card only, one icon, one orange
Details arrow, Details grows to show all text + link. The card follows the
system light/dark mode (prefers-color-scheme) and grows wider on larger
screens instead of staying phone-sized.
Icons: rain, sun, cloud, tire, wrench, bell, star, info.
"""
import argparse, html, os, sys

ICONS = {
    "rain": '<path d="M12 3a5 5 0 0 0-5 5 3.5 3.5 0 0 0 .8 6.9h8.4A3.5 3.5 0 0 0 17 8a5 5 0 0 0-5-5z"/><path d="M8 18l-1 2M12 18l-1 2M16 18l-1 2"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    "cloud": '<path d="M17.5 19a4.5 4.5 0 0 0 .4-9A7 7 0 0 0 4.3 12 3.5 3.5 0 0 0 6 19z"/>',
    "tire": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3.5"/><path d="M12 3v5M12 16v5M3 12h5M16 12h5"/>',
    "wrench": '<path d="M14.7 6.3a4.5 4.5 0 0 0-6 6L3 18l3 3 5.7-5.7a4.5 4.5 0 0 0 6-6L14 13l-3-3z"/>',
    "bell": '<path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/>',
    "star": '<path d="M12 2l3.1 6.3 6.9 1-5 4.9 1.2 6.8L12 17.8 5.8 21l1.2-6.8-5-4.9 6.9-1z"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 16v-4M12 8h.01"/>',
}

TEMPLATE = """<style>
  *{{box-sizing:border-box}}
  .glance-card{{--bg:#ffffff;--fg:#111111;--sub:#444444;--icon-bg:#fdf0dd;--divider:#d9d9d9;--panel:#222222;--accent:#b45309;--icon-stroke:#b45309;--shadow:0 8px 20px rgba(0,0,0,.12);width:100%;max-width:min(560px,100%);margin:0 auto;background:var(--bg);color:var(--fg);border:1px solid var(--divider);border-radius:18px;padding:clamp(14px,2.5vw,22px);text-align:left;box-shadow:var(--shadow);font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif}}
  @media (prefers-color-scheme: dark){{
    .glance-card{{--bg:#232323;--fg:#ffffff;--sub:#d9d9d9;--icon-bg:#3a3a3a;--divider:#3d3d3d;--panel:#e6e6e6;--accent:#ff9a3d;--icon-stroke:#ffb27a;--shadow:0 8px 20px rgba(0,0,0,.35)}}
  }}
  html[data-theme="light"] .glance-card{{--bg:#ffffff;--fg:#111111;--sub:#444444;--icon-bg:#fdf0dd;--divider:#d9d9d9;--panel:#222222;--accent:#b45309;--icon-stroke:#b45309;--shadow:0 8px 20px rgba(0,0,0,.12)}}
  html[data-theme="dark"] .glance-card{{--bg:#232323;--fg:#ffffff;--sub:#d9d9d9;--icon-bg:#3a3a3a;--divider:#3d3d3d;--panel:#e6e6e6;--accent:#ff9a3d;--icon-stroke:#ffb27a;--shadow:0 8px 20px rgba(0,0,0,.35)}}
  @media (min-width:640px){{
    .glance-card{{max-width:640px}}
  }}
  @media (min-width:1024px){{
    .glance-card{{max-width:720px}}
  }}
  .glance-head{{display:flex;gap:12px;align-items:flex-start}}
  .glance-icon{{flex:0 0 40px;width:40px;height:40px;border-radius:50%;background:var(--icon-bg);display:grid;place-items:center}}
  .glance-card h4{{margin:0;font-size:clamp(16px,2.2vw,20px);line-height:1.25;color:var(--fg)}}
  .glance-card p{{margin:4px 0 0;font-size:clamp(14px,1.8vw,16px);line-height:1.4;color:var(--sub)}}
  .glance-bullets{{margin:10px 0 0;padding-left:18px;font-size:clamp(14px,1.8vw,16px);line-height:1.5;color:var(--sub)}}
  .glance-bullets li{{margin:2px 0}}
  .glance-details-btn{{margin-top:12px;width:100%;background:transparent;border:0;border-top:1px solid var(--divider);padding:10px 0 2px;display:flex;justify-content:space-between;align-items:center;color:var(--accent);font-size:clamp(14px,1.8vw,16px);font-weight:800;cursor:pointer}}
  .glance-details-btn svg{{transition:transform .3s}}
  .glance-card.open .glance-details-btn svg{{transform:rotate(180deg)}}
  .glance-panel{{max-height:0;overflow:hidden;transition:max-height .3s ease}}
  .glance-panel div{{padding-top:8px;font-size:clamp(13px,1.6vw,15px);line-height:1.45;color:var(--panel)}}
  .glance-panel a{{color:var(--accent);text-decoration:none;font-weight:700}}
</style>
<div class="glance-card" id="glanceCard">
  <div class="glance-head">
    <span class="glance-icon" aria-hidden="true"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" style="stroke:var(--icon-stroke)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">{icon}</svg></span>
    <div>
      <h4>{header}</h4>
      <p>{subheader}</p>
    </div>
  </div>
  {bullets}
  <button class="glance-details-btn" type="button" onclick="var c=document.getElementById('glanceCard');var p=c.querySelector('.glance-panel');var open=c.classList.toggle('open');p.style.maxHeight=open?p.scrollHeight+'px':'0';"><span>Details</span><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M6 9l6 6 6-6"/></svg></button>
  <div class="glance-panel"><div>{details} <a href="{link}">{link_label}</a></div></div>
</div>
"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--header", required=True)
    ap.add_argument("--subheader", required=True)
    ap.add_argument("--details", required=True)
    ap.add_argument("--link", required=True)
    ap.add_argument("--link-label", default="Details ›")
    ap.add_argument("--icon", default="info", choices=sorted(ICONS))
    ap.add_argument("--bullet", action="append", default=[], dest="bullets",
                    help="Basic detail line shown above Details; repeat for each bullet")
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    out = os.path.expanduser(a.output)
    if not os.path.isabs(out):
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)), out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    bullets_html = ""
    if a.bullets:
        bullets_html = '<ul class="glance-bullets">' + "".join(
            f"<li>{html.escape(b)}</li>" for b in a.bullets) + "</ul>"
    html_out = TEMPLATE.format(
        icon=ICONS[a.icon],
        header=html.escape(a.header),
        subheader=html.escape(a.subheader),
        bullets=bullets_html,
        details=html.escape(a.details),
        link=html.escape(a.link, quote=True),
        link_label=html.escape(a.link_label),
    )
    with open(out, "w", encoding="utf-8") as f:
        f.write(html_out)
    print(out)

if __name__ == "__main__":
    main()
