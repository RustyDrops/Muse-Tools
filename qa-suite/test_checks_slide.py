"""Tests for qa-suite/checks_slide.py (PLAN-PHASE2.md Item 3).

Images are built synthetically in tmp_path (same geometry as
fixtures/make_slide_fixtures.py), so this file passes with or without
the committed fixture PNGs. Fixture measurements (recalibration data
for CENTRE_OFFSET_MAX_PX = 48.0):

  centred      640x360 block at x=320 -> centre (639.5, 359.5), dist ~0.7
  off-centre   640x360 block at x=460 -> centre (779.5, 359.5), dx +139.5
  edge-clipped 640x360 block at x=900 -> visible 900..1279 (380px wide),
               360px touching the right edge; centre (1089.5, 359.5)

Run: python3 -m pytest qa-suite/test_checks_slide.py -q
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"
sys.path.insert(0, str(HERE))

QA_SUITE = HERE / "qa_suite.py"

HAS_PIL = True
try:
    import PIL  # noqa: F401
except Exception:
    HAS_PIL = False

needs_pil = pytest.mark.skipif(not HAS_PIL, reason="needs PIL")

W, H = 1280, 720
BG = (255, 255, 255)
INK = (30, 41, 59)


def _slide(path, box):
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (W, H), BG)
    ImageDraw.Draw(im).rectangle(box, fill=INK)
    im.save(path)
    return path


def run_qa(*args):
    proc = subprocess.run([sys.executable, str(QA_SUITE), *args],
                          capture_output=True, text=True, timeout=600)
    try:
        verdict = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise AssertionError(f"qa_suite printed non-JSON: {proc.stdout[:500]} "
                             f"stderr: {proc.stderr[:500]}")
    return proc.returncode, verdict


@needs_pil
def test_centred_slide_passes(tmp_path):
    from checks_slide import CENTRE_OFFSET_MAX_PX, check_slide_png
    target = _slide(tmp_path / "centred.png",
                    [320, 180, 320 + 640 - 1, 180 + 360 - 1])
    verdict = check_slide_png(target)
    assert verdict["pass"] is True, verdict["failures"]
    m = verdict["measurements"]
    assert m["centre_offset_px"]["distance"] == pytest.approx(0.7, abs=1.5)
    assert m["centre_offset_px"]["distance"] <= CENTRE_OFFSET_MAX_PX
    assert all(c < 8 for c in m["edge_touch_px"].values())


@needs_pil
def test_offcentre_slide_fails_with_offset_px(tmp_path):
    from checks_slide import CENTRE_OFFSET_MAX_PX, check_slide_png
    target = _slide(tmp_path / "offcentre.png",
                    [460, 180, 460 + 640 - 1, 180 + 360 - 1])
    verdict = check_slide_png(target)
    assert verdict["pass"] is False
    kinds = [f["kind"] for f in verdict["failures"]]
    assert "off-centre" in kinds
    off = next(f for f in verdict["failures"] if f["kind"] == "off-centre")
    assert off["dx_px"] == pytest.approx(139.5, abs=1.5)
    assert off["centre_offset_px"] > CENTRE_OFFSET_MAX_PX
    assert "edge-clip" not in kinds  # fully inside the frame


@needs_pil
def test_edgeclipped_slide_fails_with_edge_kind(tmp_path):
    from checks_slide import check_slide_png
    target = _slide(tmp_path / "edgeclipped.png",
                    [900, 180, 900 + 640 - 1, 180 + 360 - 1])
    verdict = check_slide_png(target)
    assert verdict["pass"] is False
    clips = [f for f in verdict["failures"] if f["kind"] == "edge-clip"]
    assert any(f["edge"] == "right" for f in clips), verdict["failures"]
    right = next(f for f in clips if f["edge"] == "right")
    assert right["touch_px"] == 360


@needs_pil
def test_blank_slide_reuses_stddev_floor(tmp_path):
    from PIL import Image
    from checks_image import BLANK_STDDEV_FLOOR
    from checks_slide import check_slide_png
    target = tmp_path / "blank.png"
    Image.new("RGB", (W, H), (18, 18, 18)).save(target)
    verdict = check_slide_png(target)
    assert verdict["pass"] is False
    assert any(f["kind"] == "blank" for f in verdict["failures"])
    assert verdict["measurements"]["blank_floor"] == BLANK_STDDEV_FLOOR


@needs_pil
def test_missing_and_wrong_suffix_are_checker_errors(tmp_path):
    from checks_slide import check_slide_png
    missing = check_slide_png(tmp_path / "nope.png")
    assert missing["pass"] is False and "error" in missing
    txt = tmp_path / "note.txt"
    txt.write_text("not an image", encoding="utf-8")
    wrong = check_slide_png(txt)
    assert wrong["pass"] is False and "error" in wrong


@needs_pil
def test_cli_slide_check_exit_codes(tmp_path):
    centred = _slide(tmp_path / "centred.png",
                     [320, 180, 320 + 640 - 1, 180 + 360 - 1])
    code, verdict = run_qa("check", "slide", str(centred))
    assert code == 0, verdict
    assert verdict["pass"] is True
    off = _slide(tmp_path / "offcentre.png",
                 [460, 180, 460 + 640 - 1, 180 + 360 - 1])
    code, verdict = run_qa("check", "slide", str(off))
    assert code == 1, verdict
    assert verdict["pass"] is False
    assert any("centre" in f["reason"].lower()
               for f in verdict["failures"]), verdict["failures"]


@needs_pil
@pytest.mark.skipif(not (FIXTURES / "centred_slide.png").exists(),
                    reason="needs generated fixtures")
def test_committed_fixtures_match_recorded_measurements():
    from checks_slide import CENTRE_OFFSET_MAX_PX, check_slide_png
    centred = check_slide_png(FIXTURES / "centred_slide.png")
    assert centred["pass"] is True, centred["failures"]
    off = check_slide_png(FIXTURES / "offcentre_slide.png")
    assert off["pass"] is False
    assert off["measurements"]["centre_offset_px"]["distance"] > \
        CENTRE_OFFSET_MAX_PX
    clipped = check_slide_png(FIXTURES / "edgeclipped_slide.png")
    assert clipped["pass"] is False
    assert any(f["kind"] == "edge-clip" for f in clipped["failures"])
