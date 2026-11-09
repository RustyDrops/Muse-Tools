#!/usr/bin/env python3
"""Generalized deterministic QA CLI: code | image | audio.

Usage: qa_suite.py check <code|image|audio> <path> [--fix]
         [--kind shorts|sermon] [--target LUFS] [--width W --height H]

Exit 0 PASS / 1 FAIL / 2 checker-error (mirrors auto_fix.py exit codes).
Prints one JSON verdict with exact measurements per failure.
With --fix, runs the local auto-fix first (Pillow layout scripts only)
and reports `unfixable` (with measurements) when a Luna fix round is
justified. Never calls Luna itself; luna_cost_usd is always 0.0.
Gate semantics (socialforge/qa.py): runs last, blocks on FAIL.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

REUSE_LAYOUT_DIR = "/home/hatch/workspace/openai-batch-test-2026-11-05"


def _check_code(path):
    import checks_code
    return checks_code.check_code_file(path)


def _check_image(path, width=None, height=None):
    import checks_image
    suffix = Path(path).suffix.lower()
    if suffix == ".py":
        return checks_image.check_image_script(path)
    if suffix in (".png", ".jpg", ".jpeg"):
        return checks_image.check_rendered_png(path, width, height)
    return {"pass": False,
            "error": f"image check needs .py or .png/.jpg, got '{suffix}'",
            "failures": []}


def _check_audio(path, kind, target):
    import checks_audio
    return checks_audio.check_audio_file(path, kind=kind, target=target)


def _check_slide(path):
    import checks_slide
    return checks_slide.check_slide_png(path)


def _try_local_fix(kind, path):
    """Local auto-fix first. Returns (fix_result_or_None, note)."""
    if kind == "image" and Path(path).suffix.lower() == ".py":
        sys.path.insert(0, REUSE_LAYOUT_DIR)
        try:
            from auto_fix import auto_fix_file
        except Exception as exc:
            return None, f"auto-fix import failed: {exc}"
        try:
            return auto_fix_file(path), None
        except Exception as exc:
            return None, f"auto-fix crashed: {exc}"
    return None, "no local auto-fix applies to this kind (code/audio fail straight to verdict)"


def main(argv):
    if len(argv) < 3 or argv[0] != "check" or argv[1] not in (
            "code", "image", "audio", "slide"):
        print("usage: qa_suite.py check <code|image|audio|slide> <path> [--fix] "
              "[--kind shorts|sermon] [--target LUFS] [--width W --height H]",
              file=sys.stderr)
        return 2
    kind, path = argv[1], argv[2]
    fix = "--fix" in argv
    kkind, target, width, height = "shorts", None, None, None
    args = argv[3:]
    i = 0
    while i < len(args):
        if args[i] == "--kind" and i + 1 < len(args):
            kkind, i = args[i + 1], i + 2
        elif args[i] == "--target" and i + 1 < len(args):
            target, i = float(args[i + 1]), i + 2
        elif args[i] == "--width" and i + 1 < len(args):
            width, i = int(args[i + 1]), i + 2
        elif args[i] == "--height" and i + 1 < len(args):
            height, i = int(args[i + 1]), i + 2
        else:
            i += 1

    verdict = {"tool": "qa-suite", "kind": kind, "path": str(path),
               "fix_requested": fix, "fixed": False, "fixes_applied": [],
               "unfixable": False, "reasons": [], "luna_cost_usd": 0.0}

    if kind == "code":
        check = _check_code(path)
    elif kind == "image":
        check = _check_image(path, width, height)
    elif kind == "slide":
        check = _check_slide(path)
    else:
        check = _check_audio(path, kkind, target)

    if check.get("error") and not check.get("failures"):
        verdict.update(pass_=False, error=check["error"],
                       failures=[], measurements=check.get("measurements"))
        verdict["pass"] = verdict.pop("pass_")
        print(json.dumps(verdict, indent=2))
        return 2

    if fix and not check.get("pass"):
        fix_result, note = _try_local_fix(kind, path)
        if fix_result is not None:
            verdict["fixed"] = bool(fix_result.get("pass"))
            verdict["fixes_applied"] = fix_result.get("fixes_applied", [])
            verdict["iterations"] = fix_result.get("iterations", 0)
            if fix_result.get("error"):
                verdict.update(pass_=False,
                               error=fix_result["error"], failures=[],
                               measurements=fix_result.get("check"))
                verdict["pass"] = verdict.pop("pass_")
                print(json.dumps(verdict, indent=2))
                return 2
            # Re-read the verdict from the (possibly rewritten) file.
            if kind == "image":
                check = _check_image(path, width, height)
            if not check.get("pass"):
                verdict["unfixable"] = True
                verdict["reasons"] = fix_result.get("reasons", [])
        else:
            verdict["fix_note"] = note
            verdict["unfixable"] = True
            verdict["reasons"] = [
                "no local auto-fix applies; a Luna round with the "
                "attached measurements is justified"]
    elif fix and check.get("pass"):
        verdict["fix_note"] = "already passing; no-op, file not rewritten"

    verdict["pass"] = bool(check.get("pass"))
    verdict["failures"] = check.get("failures", [])
    verdict["measurements"] = check.get("measurements")
    if check.get("error"):
        verdict["error"] = check["error"]
    print(json.dumps(verdict, indent=2))
    if verdict.get("error") and not verdict["failures"]:
        return 2
    return 0 if verdict["pass"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
