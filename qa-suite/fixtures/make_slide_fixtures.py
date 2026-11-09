#!/usr/bin/env python3
"""Generate the three synthetic slide fixtures (1280x720 PNGs).

Run: python3 qa-suite/fixtures/make_slide_fixtures.py
White background, one dark-slate content block; no real decks, no text,
no personal media. Fixture geometry (measured expectations live in
qa-suite/test_checks_slide.py):

  centred_slide.png    640x360 block at (320, 180) -> offset ~0px, PASS
  offcentre_slide.png  640x360 block at (460, 180) -> dx +140px, FAIL
  edgeclipped_slide.png  640x360 block at (900, 180) -> runs past the
                         right frame edge, clipped to 380px visible
                         with 360px touching the edge, FAIL
"""

from pathlib import Path

from PIL import Image, ImageDraw

W, H = 1280, 720
BG = (255, 255, 255)
INK = (30, 41, 59)

HERE = Path(__file__).resolve().parent


def _slide(name, box):
    im = Image.new("RGB", (W, H), BG)
    ImageDraw.Draw(im).rectangle(box, fill=INK)
    im.save(HERE / name)
    print(f"wrote {name} box={box}")


if __name__ == "__main__":
    _slide("centred_slide.png", [320, 180, 320 + 640 - 1, 180 + 360 - 1])
    _slide("offcentre_slide.png", [460, 180, 460 + 640 - 1, 180 + 360 - 1])
    _slide("edgeclipped_slide.png", [900, 180, 900 + 640 - 1, 180 + 360 - 1])
