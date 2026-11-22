#!/usr/bin/env python3
"""Frame-by-frame render of film.html via window.renderAt(t), piped to ffmpeg.
Known working Chromium flags on this VM: swiftshader ANGLE, NO --disable-gpu.
Run with the tools venv:  ~/workspace/tools-venv/bin/python render.py
"""
import asyncio, subprocess, sys, time
from pathlib import Path
from playwright.async_api import async_playwright

HERE = Path(__file__).resolve().parent
URL = (HERE / "film.html").as_uri() + "?render=1"
SECS, FPS, W, H = 8, 60, 1920, 1080
GPU = ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"]

async def main():
    out = HERE / "film.mp4"
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-f", "image2pipe", "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p",
         "-movflags", "+faststart", str(out)],
        stdin=subprocess.PIPE)
    t0 = time.time()
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=GPU)
        page = await browser.new_page(viewport={"width": W, "height": H})
        await page.goto(URL)
        await page.wait_for_function("window.__ready === true")
        for i in range(SECS * FPS):  # frames 0..479, never frame 480
            await page.evaluate(f"window.renderAt({i / FPS})")
            ff.stdin.write(await page.screenshot(type="png"))
            if i % 120 == 0:
                print(f"frame {i} elapsed {time.time()-t0:.1f}s", flush=True)
        await browser.close()
    ff.stdin.close(); ff.wait()
    print(f"done in {time.time()-t0:.1f}s -> {out} rc={ff.returncode}")

if __name__ == "__main__":
    asyncio.run(main())
