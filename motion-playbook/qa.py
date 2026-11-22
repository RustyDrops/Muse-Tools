#!/usr/bin/env python3
"""QA for film.html: stills + hero-width (pixel-measured), seek purity check,
loop seam diff. freezedetect / ffprobe are run separately (see QA.md).
Run: ~/workspace/tools-venv/bin/python qa.py
Outputs PNGs + qa_results.json in ./qa/
"""
import asyncio, io, json
from pathlib import Path
from PIL import Image, ImageChops
from playwright.async_api import async_playwright

HERE = Path(__file__).resolve().parent
QA = HERE / "qa"; QA.mkdir(exist_ok=True)
URL = (HERE / "film.html").as_uri() + "?render=1"
GPU = ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"]
ACCENT = (0xD9, 0x77, 0x57)

def accent_bbox(img: Image.Image):
    """Bounding box of accent-coloured pixels (the mascot is the only accent)."""
    px = img.convert("RGB")
    import numpy as np
    a = np.asarray(px).astype(int)
    mask = (abs(a[..., 0]-ACCENT[0]) < 12) & (abs(a[..., 1]-ACCENT[1]) < 12) & (abs(a[..., 2]-ACCENT[2]) < 12)
    ys, xs = mask.nonzero()
    if len(xs) == 0: return None
    return {"x_min": int(xs.min()), "x_max": int(xs.max()), "y_min": int(ys.min()), "y_max": int(ys.max()),
            "width_px": int(xs.max()-xs.min()+1), "height_px": int(ys.max()-ys.min()+1), "accent_px": int(len(xs))}

def mean_abs_diff(im1: Image.Image, im2: Image.Image) -> float:
    import numpy as np
    a = np.asarray(im1.convert("RGB")).astype(int)
    b = np.asarray(im2.convert("RGB")).astype(int)
    return float(abs(a-b).mean())

async def shot(page, t):
    await page.evaluate(f"window.renderAt({t})")
    return Image.open(io.BytesIO(await page.screenshot(type="png")))

async def main():
    results = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=GPU)
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        await page.goto(URL)
        await page.wait_for_function("window.__ready === true")

        # 1. Stills + hero width
        results["stills"] = {}
        for t in (0.5, 1.8, 3.0, 4.6):
            img = await shot(page, t)
            img.save(QA / f"still_{t}s.png")
            results["stills"][str(t)] = accent_bbox(img)
            print(t, results["stills"][str(t)])

        # 2. Seek check: frame 300 after frame 299 (same page)
        await shot(page, 299/60)
        img_seq = await shot(page, 300/60)
        img_seq.save(QA / "frame300_after_299.png")

        # 4. Seam frames (same page, sequential)
        f0 = await shot(page, 0)
        f479 = await shot(page, 479/60)
        f0.save(QA / "frame000.png"); f479.save(QA / "frame479.png")
        results["seam_mean_abs_diff_479_vs_0"] = mean_abs_diff(f479, f0)
        results["seam_bbox_479"] = accent_bbox(f479)
        results["seam_bbox_0"] = accent_bbox(f0)
        await browser.close()

        # 2b. Frame 300 cold: fresh browser/page, first thing rendered
        browser = await p.chromium.launch(args=GPU)
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        await page.goto(URL)
        await page.wait_for_function("window.__ready === true")
        img_cold = await shot(page, 300/60)
        img_cold.save(QA / "frame300_cold.png")
        await browser.close()

    results["seek_frame300_mean_abs_diff"] = mean_abs_diff(img_cold, img_seq)
    results["seek_frame300_max_channel_diff"] = int(
        max(abs(int(a)-int(b)) for a, b in zip(
            ImageChops.difference(img_cold.convert("RGB"), img_seq.convert("RGB"))
            .convert("L").getdata(), [0]* (1920*1080))) if False else
        ImageChops.difference(img_cold.convert("RGB"), img_seq.convert("RGB"))
        .convert("L").getextrema()[1])
    (QA / "qa_results.json").write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
