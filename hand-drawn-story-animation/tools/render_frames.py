#!/usr/bin/env python3
"""Render a hand-drawn story scene HTML to frames and (optionally) an MP4.

Usage:
  render_frames.py --scene scene.html --frames frames/ [--scale 1|2] [--fps 12]
                   [--dur 15] [--mp4 out.mp4] [--probe 7.5,11,14.5]

Sizes: --scale 1 = 540x960 draft (fast, for checking), --scale 2 = 1080x1920
production. The scene is vector, so both come from the same file.
--probe renders only the listed timestamps (seconds) as PNGs into --frames,
for quick art checks before paying for a full render.
Always prints console errors and a seek-purity check (cold render of the
middle probe frame vs the sequential frame, mean absolute pixel diff).
"""
import argparse, glob, os, subprocess, sys

sys.path.insert(0, os.path.expanduser("~/workspace/tools-venv/lib/python3.12/site-packages"))


def find_chromium():
    hits = sorted(glob.glob(os.path.expanduser(
        "~/.cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell")))
    if not hits:
        raise SystemExit("no Playwright headless shell found in ~/.cache/ms-playwright")
    return hits[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", required=True)
    ap.add_argument("--frames", required=True)
    ap.add_argument("--scale", type=int, default=1, choices=[1, 2])
    ap.add_argument("--fps", type=int, default=12)
    ap.add_argument("--dur", type=float, default=15)
    ap.add_argument("--mp4", default="")
    ap.add_argument("--probe", default="")
    a = ap.parse_args()
    os.makedirs(a.frames, exist_ok=True)
    from playwright.sync_api import sync_playwright
    W, H = 540 * a.scale, 960 * a.scale
    url = "file://" + os.path.abspath(a.scene)
    probes = [float(x) for x in a.probe.split(",") if x] if a.probe else None
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=find_chromium(),
                               args=["--use-gl=angle", "--use-angle=swiftshader",
                                     "--enable-unsafe-swiftshader"])
        pg = b.new_page(viewport={"width": W, "height": H})
        errors = []
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(url)
        pg.wait_for_function("window.__ready === true")
        if a.scale == 2:
            pg.evaluate("document.getElementById('stage').style.transform='scale(2)';"
                        "document.getElementById('stage').style.transformOrigin='0 0';")
        if probes:
            for t in probes:
                pg.evaluate(f"window.renderAt({t})")
                pg.screenshot(path=os.path.join(a.frames, f"probe_{t}.png"))
            print("probes done:", probes)
        else:
            n = int(a.fps * a.dur)
            mid = n // 2
            for i in range(n):
                pg.evaluate(f"window.renderAt({i / a.fps})")
                pg.screenshot(path=os.path.join(a.frames, f"frame_{i:03d}.png"))
            pg2 = b.new_page(viewport={"width": W, "height": H})
            pg2.goto(url)
            pg2.wait_for_function("window.__ready === true")
            if a.scale == 2:
                pg2.evaluate("document.getElementById('stage').style.transform='scale(2)';"
                             "document.getElementById('stage').style.transformOrigin='0 0';")
            pg2.evaluate(f"window.renderAt({mid / a.fps})")
            cold = os.path.join(a.frames, "cold_mid.png")
            pg2.screenshot(path=cold)
            from PIL import Image
            import numpy as np
            x = np.asarray(Image.open(os.path.join(a.frames, f"frame_{mid:03d}.png")).convert("RGB"), dtype=int)
            y = np.asarray(Image.open(cold).convert("RGB"), dtype=int)
            print("seek_purity_mean_abs_diff", abs(x - y).mean())
            print("frames done", n)
        b.close()
    print("console_errors:", errors)
    if a.mp4 and not probes:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(a.fps),
                        "-i", os.path.join(a.frames, "frame_%03d.png"),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.mp4],
                       check=True)
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration,size",
                              "-show_entries", "stream=width,height,codec_name",
                              "-of", "default=noprint_wrappers=1", a.mp4],
                             capture_output=True, text=True)
        print(out.stdout)


if __name__ == "__main__":
    main()
