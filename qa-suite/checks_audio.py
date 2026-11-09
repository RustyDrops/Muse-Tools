"""Audio checker: ffprobe format/duration/sample-rate + loudness gate.

Loudness uses the existing two-pass loudnorm measurement pattern from
socialforge/creators/audio.py (measure first, tolerance 1 LUFS as in
creators/shorts.py): target -14 LUFS for Shorts, -16 LUFS for sermon.
Never re-cleans or re-encodes; measurement only. Missing ffmpeg/ffprobe
is a checker error (exit 2 upstream), never a FAIL.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

# Targets from creators/shorts.py + creators/audio.py; tolerance 1 LUFS.
TARGETS = {"shorts": -14.0, "sermon": -16.0}
LOUDNESS_TOLERANCE_LUFS = 1.0
TRUE_PEAK_CEILING_DBTP = -1.0


def _run(cmd):
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except FileNotFoundError as exc:
        return {"error": f"runner not found: {exc}"}
    except subprocess.TimeoutExpired:
        return {"error": "ffmpeg/ffprobe timed out"}
    return {"returncode": proc.returncode,
            "stdout": proc.stdout, "stderr": proc.stderr}


def probe(path):
    """ffprobe format + stream facts. {"error": ...} when unavailable."""
    if shutil.which("ffprobe") is None:
        return {"error": "ffprobe not on PATH"}
    p = Path(path)
    if not p.exists():
        return {"error": f"target not found: {path}"}
    res = _run(["ffprobe", "-hide_banner", "-v", "quiet",
                "-print_format", "json", "-show_format", "-show_streams",
                str(p)])
    if "error" in res:
        return res
    if res["returncode"] != 0:
        return {"error": f"ffprobe exit {res['returncode']}: "
                         f"{res['stderr'][:300]}"}
    try:
        return {"probe": json.loads(res["stdout"])}
    except json.JSONDecodeError as exc:
        return {"error": f"ffprobe output not JSON: {exc}"}


def measure_loudness(path):
    """Single loudnorm analysis pass (the measurement half of the
    two-pass pattern in creators/audio.py _loudnorm_measure)."""
    if shutil.which("ffmpeg") is None:
        return {"error": "ffmpeg not on PATH"}
    filt = "loudnorm=print_format=json"
    res = _run(["ffmpeg", "-hide_banner", "-i", str(path),
                "-vn", "-af", filt, "-f", "null", "-"])
    if "error" in res:
        return res
    m = re.search(r"\{[^}]*\"input_i\"[^}]*\}", res["stderr"], re.S)
    if not m:
        return {"error": "loudnorm measurement failed: no JSON in output"}
    try:
        return {"loudness": json.loads(m.group(0))}
    except json.JSONDecodeError as exc:
        return {"error": f"loudnorm JSON unparsable: {exc}"}


def check_audio_file(path, kind="shorts", target=None,
                     min_duration_s=None, max_duration_s=None):
    """Gate an audio/video file. kind selects the loudness target when
    target is None. Duration bounds are checked only when given."""
    if kind not in TARGETS and target is None:
        return {"pass": False,
                "error": f"unknown kind '{kind}'; pass explicit target",
                "failures": []}
    want = float(target) if target is not None else TARGETS[kind]
    probed = probe(path)
    if "error" in probed:
        return {"pass": False, "error": probed["error"], "failures": []}
    fmt = probed["probe"].get("format", {})
    streams = probed["probe"].get("streams", [])
    audio = [s for s in streams if s.get("codec_type") == "audio"]
    failures, measurements = [], {}
    try:
        duration = float(fmt.get("duration", "nan"))
    except ValueError:
        duration = float("nan")
    measurements["duration_s"] = duration
    measurements["format"] = fmt.get("format_name")
    measurements["sample_rate_hz"] = None
    measurements["channels"] = None
    if not audio:
        failures.append({"kind": "no-audio-stream",
                         "reason": "no audio stream in file"})
    else:
        a0 = audio[0]
        try:
            sr = int(a0.get("sample_rate", 0))
        except ValueError:
            sr = 0
        measurements["sample_rate_hz"] = sr
        measurements["channels"] = a0.get("channels")
        measurements["codec"] = a0.get("codec_name")
        if sr <= 0:
            failures.append({"kind": "sample-rate",
                             "reason": f"bad sample rate: "
                                       f"{a0.get('sample_rate')}"})
    if min_duration_s is not None and not (duration >= min_duration_s):
        failures.append({"kind": "duration",
                         "reason": f"duration {duration:.2f}s < "
                                   f"minimum {min_duration_s}s",
                         "duration_s": duration})
    if max_duration_s is not None and not (duration <= max_duration_s):
        failures.append({"kind": "duration",
                         "reason": f"duration {duration:.2f}s > "
                                   f"maximum {max_duration_s}s",
                         "duration_s": duration})
    loud = measure_loudness(path)
    if "error" in loud:
        return {"pass": False, "error": loud["error"], "failures": []}
    integrated = float(loud["loudness"]["input_i"])
    true_peak = float(loud["loudness"]["input_tp"])
    measurements["integrated_lufs"] = round(integrated, 2)
    measurements["true_peak_dbtp"] = round(true_peak, 2)
    measurements["target_lufs"] = want
    measurements["tolerance_lufs"] = LOUDNESS_TOLERANCE_LUFS
    if abs(integrated - want) > LOUDNESS_TOLERANCE_LUFS:
        failures.append({
            "kind": "loudness",
            "reason": (f"integrated {integrated:.2f} LUFS vs target "
                       f"{want:.1f} LUFS (tolerance "
                       f"{LOUDNESS_TOLERANCE_LUFS:.1f} LUFS)"),
            "integrated_lufs": round(integrated, 2),
            "target_lufs": want})
    if true_peak > TRUE_PEAK_CEILING_DBTP:
        failures.append({
            "kind": "true-peak",
            "reason": (f"true peak {true_peak:.2f} dBTP above ceiling "
                       f"{TRUE_PEAK_CEILING_DBTP:.1f} dBTP"),
            "true_peak_dbtp": round(true_peak, 2)})
    return {"pass": not failures, "failures": failures,
            "measurements": measurements}
