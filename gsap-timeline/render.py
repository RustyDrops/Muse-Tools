import hashlib, pathlib, sys
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).parent
FRAMES = HERE / "frames"; FRAMES.mkdir(exist_ok=True)
FPS, DUR = 30, 3.0
url = (HERE / "index.html").as_uri()

with sync_playwright() as p:
    b = p.chromium.launch(args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
    pg = b.new_page(viewport={"width": 720, "height": 720})
    pg.goto(url); pg.wait_for_function("window.__ready === true")
    dur = pg.evaluate("window.__duration")
    print(f"timeline duration: {dur:.3f}s (rendering {DUR}s at {FPS}fps)")
    # determinism check: same t twice
    hashes = []
    for i in range(2):
        pg.evaluate(f"window.renderAt(1.0)")
        shot = pg.screenshot()
        hashes.append(hashlib.sha256(shot).hexdigest()[:16])
    print("determinism t=1.0:", hashes, "MATCH" if hashes[0] == hashes[1] else "MISMATCH")
    n = int(FPS * DUR)
    for f in range(n):
        pg.evaluate(f"window.renderAt({f / FPS:.4f})")
        pg.screenshot(path=str(FRAMES / f"f{f:03d}.png"))
    b.close()
print(f"frames: {n}")
