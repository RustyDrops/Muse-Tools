"""Fixture tests for the generalized deterministic QA suite.

Covers the three auto_fix proof cases from the handoff:
  1. turn-1 FAIL must reach PASS via local auto-fix (bad_layout.py);
  2. below-floor type must be RESTORED, never passed (below_floor_layout.py);
  3. already-passing input is a no-op (good_layout.py).
Plus code (good/bad pytest targets), image PNG (blank/non-blank),
contrast-unit, and audio (ffprobe/loudnorm measurement) gates.

Run with the tools-venv python (it has pytest; system python3 does not):
  ~/workspace/tools-venv/bin/python -m pytest qa-suite/test_qa_suite.py -q
"""

import json
import math
import shutil
import struct
import subprocess
import sys
import wave
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"
sys.path.insert(0, str(HERE))

TOOLS_VENV_PYTHON = "/home/hatch/workspace/tools-venv/bin/python"
QA_SUITE = HERE / "qa_suite.py"

HAS_PIL = True
try:
    import PIL  # noqa: F401
except Exception:
    HAS_PIL = False

HAS_FONTS = (Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf").exists()
             and Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf").exists())
HAS_FFMPEG = shutil.which("ffmpeg") is not None
HAS_FFPROBE = shutil.which("ffprobe") is not None

needs_layout = pytest.mark.skipif(
    not (HAS_PIL and HAS_FONTS),
    reason="needs PIL + DejaVu fonts for check_layout")
needs_media = pytest.mark.skipif(
    not (HAS_FFMPEG and HAS_FFPROBE),
    reason="needs ffmpeg + ffprobe for audio checks")
needs_venv = pytest.mark.skipif(
    not Path(TOOLS_VENV_PYTHON).exists(),
    reason="needs tools-venv python for pytest runs")


def run_qa(*args):
    proc = subprocess.run([sys.executable, str(QA_SUITE), *args],
                          capture_output=True, text=True, timeout=600)
    try:
        verdict = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise AssertionError(f"qa_suite printed non-JSON: {proc.stdout[:500]} "
                             f"stderr: {proc.stderr[:500]}")
    return proc.returncode, verdict


def copy_fixture(name, tmp_path):
    dest = tmp_path / name
    dest.write_text((FIXTURES / name).read_text(encoding="utf-8"),
                    encoding="utf-8")
    return dest


# --- image/layout proof cases ---

@needs_layout
def test_good_layout_passes_and_fix_is_noop(tmp_path):
    target = copy_fixture("good_layout.py", tmp_path)
    before = target.read_bytes()
    code, verdict = run_qa("check", "image", str(target), "--fix")
    assert code == 0, verdict
    assert verdict["pass"] is True
    assert verdict["luna_cost_usd"] == 0.0
    assert target.read_bytes() == before  # no-op: not rewritten


@needs_layout
def test_bad_layout_turn1_fail_reaches_pass(tmp_path):
    target = copy_fixture("bad_layout.py", tmp_path)
    code0, before = run_qa("check", "image", str(target))
    assert code0 == 1, before
    assert before["pass"] is False
    assert before["failures"], "FAIL must carry exact measurements"
    code, verdict = run_qa("check", "image", str(target), "--fix")
    assert code == 0, verdict
    assert verdict["pass"] is True
    assert verdict["fixed"] is True
    assert verdict["fixes_applied"], "must name the local fixes applied"
    assert verdict["luna_cost_usd"] == 0.0


@needs_layout
def test_below_floor_type_restored_never_passed(tmp_path):
    target = copy_fixture("below_floor_layout.py", tmp_path)
    code, verdict = run_qa("check", "image", str(target), "--fix")
    assert code == 1, verdict
    assert verdict["pass"] is False
    assert verdict["unfixable"] is True
    assert verdict["reasons"], "unfixable must carry exact px reasons"
    assert any("px" in r for r in verdict["reasons"])
    src = target.read_text(encoding="utf-8")
    assert "bold_font(34)" in src, "title must be restored to the floor"
    assert "regular_font(28)" in src, "body must be restored to the floor"
    assert "bold_font(20)" not in src and "regular_font(18)" not in src


@needs_layout
def test_extractor_error_is_checker_error(tmp_path):
    target = tmp_path / "unparseable_shape.py"
    target.write_text("x = 1\n", encoding="utf-8")
    code, verdict = run_qa("check", "image", str(target))
    assert code == 2, verdict
    assert "error" in verdict  # never a Luna round, never a PASS


# --- code checker ---

def _write_test_file(tmp_path, name, body):
    target = tmp_path / name
    target.write_text(body, encoding="utf-8")
    return target


@needs_venv
def test_code_good_target_passes(tmp_path):
    from checks_code import check_code_file
    target = _write_test_file(
        tmp_path, "test_sample_ok.py",
        "def test_addition():\n    assert 1 + 1 == 2\n")
    verdict = check_code_file(target, log_dir=tmp_path)
    assert verdict["pass"] is True, verdict["failures"]
    assert Path(verdict["log_path"]).exists()


@needs_venv
def test_code_bad_target_lists_tests_not_logs(tmp_path):
    from checks_code import check_code_file
    target = _write_test_file(
        tmp_path, "test_sample_bad.py",
        "def test_broken():\n    assert 1 == 2, 'off by one'\n")
    verdict = check_code_file(target, log_dir=tmp_path)
    assert verdict["pass"] is False
    names = [f["test"] for f in verdict["failures"]]
    assert any("test_broken" in n for n in names), names
    assert all("path" in f for f in verdict["failures"])
    assert Path(verdict["log_path"]).exists()
    full = Path(verdict["log_path"]).read_text(encoding="utf-8")
    assert "test_broken" in full


# --- rendered PNG + contrast ---

@pytest.mark.skipif(not HAS_PIL, reason="needs PIL")
def test_rendered_png_blank_floor(tmp_path):
    from PIL import Image, ImageDraw
    from checks_image import check_rendered_png
    good = tmp_path / "good.png"
    base = Image.new("RGB", (1080, 1080), (30, 30, 30))
    draw = ImageDraw.Draw(base)
    draw.rectangle([0, 0, 539, 1079], fill=(200, 30, 30))
    draw.rectangle([540, 0, 1079, 539], fill=(30, 200, 30))
    base.save(good)
    verdict = check_rendered_png(good, width=1080, height=1080)
    assert verdict["pass"] is True, verdict
    assert verdict["measurements"]["size"] == [1080, 1080]
    blank = tmp_path / "blank.png"
    Image.new("RGB", (1080, 1080), (18, 18, 18)).save(blank)
    verdict = check_rendered_png(blank, width=1080, height=1080)
    assert verdict["pass"] is False
    assert any(f["kind"] == "blank" for f in verdict["failures"])
    assert any("stddev" in f["reason"] for f in verdict["failures"])
    small = tmp_path / "small.png"
    Image.new("RGB", (100, 100), (30, 30, 30)).save(small)
    verdict = check_rendered_png(small, width=1080, height=1080)
    assert verdict["pass"] is False
    assert any(f["kind"] == "dimensions" for f in verdict["failures"])


def test_contrast_thresholds():
    from checks_image import check_contrast
    bw = check_contrast("#000000", "#ffffff", "body")
    assert bw["pass"] is True
    assert bw["ratio"] >= 15  # ~21:1, far above the 4.5:1 body floor
    same = check_contrast("#777777", "#777777", "body")
    assert same["pass"] is False
    assert same["ratio"] == pytest.approx(1.0)


# --- audio checker ---

def _write_tone_wav(path, seconds=2.0, freq=440.0, peak=0.4, rate=44100):
    n = int(seconds * rate)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        for i in range(n):
            v = int(peak * 32767 * math.sin(2 * math.pi * freq * i / rate))
            w.writeframes(struct.pack("<h", v))
    return path


@needs_media
def test_audio_probe_and_loudness_measurements(tmp_path):
    from checks_audio import check_audio_file
    wav = _write_tone_wav(tmp_path / "tone.wav")
    verdict = check_audio_file(wav, kind="shorts")
    assert "error" not in verdict, verdict.get("error")
    m = verdict["measurements"]
    assert m["sample_rate_hz"] == 44100
    assert m["target_lufs"] == -14.0
    assert isinstance(m["integrated_lufs"], float)
    assert m["duration_s"] == pytest.approx(2.0, abs=0.1)
    sermon = check_audio_file(wav, kind="sermon")
    assert sermon["measurements"]["target_lufs"] == -16.0


@needs_media
def test_audio_duration_bound_reports_seconds(tmp_path):
    from checks_audio import check_audio_file
    wav = _write_tone_wav(tmp_path / "short.wav", seconds=2.0)
    verdict = check_audio_file(wav, kind="shorts", min_duration_s=5.0)
    assert verdict["pass"] is False
    assert any(f["kind"] == "duration" and "2.00s" in f["reason"]
               for f in verdict["failures"])
