#!/usr/bin/env python3
"""Toolbox CLI dispatcher. Usage: toolbox.py <command> <args> [--json] [--out PATH]

Exit codes (mirror qa-suite): 0 pass/found, 1 fail/not-found, 2 tool error.
Every command prints ONE short JSON object; never a whole file.
Stdlib only.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import draft_tools
import python_tools
import validate_tools


def _usage():
    return ("usage: toolbox.py <command> <args> [--json] [--out PATH]\n"
            "commands: peek grep diff stats outline strip toc check-url "
            "syntax imports validate scaffold diagram canary health "
            "estimate-cost")


def _take(args, i):
    val = args[i + 1]
    del args[i:i + 2]
    return val


def _has(args, *names):
    for i, a in enumerate(args):
        if a in names:
            args.pop(i)
            return True
    return False


def _reject_dir(args):
    if "--dir" in args:
        return (2, {"error": "grep --dir is out of scope; single file only"})
    return None


def dispatch(cmd, args):
    """Run one command. Returns (exit_code, payload_dict)."""
    if cmd == "peek":
        _has(args, "--json")
        if len(args) != 3:
            return 2, {"error": "usage: peek <path> <start> <end>"}
        return draft_tools.peek(*args)
    if cmd == "grep":
        _has(args, "--json")
        hit = _reject_dir(args)
        if hit:
            return hit
        ic = _has(args, "--ignore-case")
        rx = _has(args, "--regex")
        if len(args) != 2:
            return 2, {"error": "usage: grep <path> <pattern> "
                                "[--ignore-case] [--regex]"}
        return draft_tools.grep(args[0], args[1],
                                ignore_case=ic, regex=rx)
    if cmd == "diff":
        _has(args, "--json")
        if len(args) != 2:
            return 2, {"error": "usage: diff <old> <new>"}
        return draft_tools.diff(*args)
    if cmd == "stats":
        _has(args, "--json")
        if len(args) != 1:
            return 2, {"error": "usage: stats <path>"}
        return draft_tools.stats(*args)
    if cmd == "toc":
        _has(args, "--json")
        if len(args) != 1:
            return 2, {"error": "usage: toc <mdfile>"}
        return draft_tools.toc(*args)
    if cmd == "strip":
        _has(args, "--json")
        out = None
        if "--out" in args:
            i = args.index("--out")
            if i + 1 >= len(args):
                return 2, {"error": "strip: --out needs a PATH"}
            out = _take(args, i)
        if len(args) != 1:
            return 2, {"error": "usage: strip <pyfile> [--out PATH]"}
        return draft_tools.strip(args[0], out=out)
    if cmd == "outline":
        _has(args, "--json")
        if len(args) != 1:
            return 2, {"error": "usage: outline <pyfile>"}
        return python_tools.outline(*args)
    if cmd == "syntax":
        _has(args, "--json")
        if len(args) != 1:
            return 2, {"error": "usage: syntax <pyfile>"}
        return python_tools.syntax(*args)
    if cmd == "imports":
        _has(args, "--json")
        if len(args) != 1:
            return 2, {"error": "usage: imports <pyfile>"}
        return python_tools.imports(*args)
    if cmd == "scaffold":
        _has(args, "--json")
        out = None
        if "--out" in args:
            i = args.index("--out")
            if i + 1 >= len(args):
                return 2, {"error": "scaffold: --out needs a PATH"}
            out = _take(args, i)
        force = _has(args, "--force")
        if len(args) != 1:
            return 2, {"error": "usage: scaffold <pyfile> [--out PATH] "
                                "[--force]"}
        return python_tools.scaffold(args[0], out=out, force=force)
    if cmd == "diagram":
        _has(args, "--json")
        out = None
        if "--out" in args:
            i = args.index("--out")
            if i + 1 >= len(args):
                return 2, {"error": "diagram: --out needs a PATH"}
            out = _take(args, i)
        if len(args) != 1:
            return 2, {"error": "usage: diagram <pyfile> [--out PATH]"}
        return python_tools.diagram(args[0], out=out)
    if cmd == "canary":
        _has(args, "--json")
        timeout = 10
        if "--timeout" in args:
            i = args.index("--timeout")
            if i + 1 >= len(args):
                return 2, {"error": "canary: --timeout needs a value"}
            timeout = _take(args, i)
        if len(args) != 1:
            return 2, {"error": "usage: canary <pyfile> [--timeout N]"}
        return python_tools.canary(args[0], timeout=timeout)
    if cmd == "check-url":
        _has(args, "--json")
        if len(args) != 1:
            return 2, {"error": "usage: check-url <url>"}
        return validate_tools.check_url(args[0])
    if cmd == "validate":
        _has(args, "--json")
        if len(args) != 2:
            return 2, {"error": "usage: validate <jsonfile> <schemafile>"}
        return validate_tools.validate(*args)
    if cmd == "health":
        _has(args, "--json")
        if args:
            return 2, {"error": "usage: health (no args)"}
        return validate_tools.health()
    if cmd == "estimate-cost":
        _has(args, "--json")
        rates = None
        if "--rates" in args:
            i = args.index("--rates")
            if i + 1 >= len(args):
                return 2, {"error": "estimate-cost: --rates needs a PATH"}
            rates = _take(args, i)
        out_n = 0
        if "--output-tokens" in args:
            i = args.index("--output-tokens")
            if i + 1 >= len(args):
                return 2, {"error": "estimate-cost: --output-tokens needs N"}
            out_n = _take(args, i)
        if len(args) != 1:
            return 2, {"error": "usage: estimate-cost <path> "
                                "[--output-tokens N] [--rates PATH]"}
        return validate_tools.estimate_cost(args[0], output_tokens=out_n,
                                            rates=rates)
    return 2, {"error": f"unknown command: {cmd}\n{_usage()}"}


def main(argv):
    if len(argv) < 2:
        print(json.dumps({"command": None, "ok": False,
                          "error": _usage()}))
        return 2
    cmd, rest = argv[1], list(argv[2:])
    code, payload = dispatch(cmd, rest)
    if not isinstance(payload, dict):
        payload = {"result": payload}
    payload = {"command": cmd, "ok": code == 0, **payload}
    print(json.dumps(payload))
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv))
