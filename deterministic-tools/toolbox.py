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
import hallmark_tools
import improve_tools
import python_tools
import validate_tools


def _usage():
    return ("usage: toolbox.py <command> <args> [--json] [--out PATH]\n"
            "commands: peek grep diff stats outline strip toc check-url "
            "syntax imports validate scaffold diagram canary health "
            "estimate-cost stamp drift branch-scope rejected "
            "snapshot kept words gatecheck deal rotation brief")


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
    if cmd == "stamp":
        _has(args, "--json")
        force = _has(args, "--force")
        if len(args) < 2:
            return 2, {"error": "usage: stamp <out.json> <path> [path...] "
                                "[--force]"}
        return improve_tools.stamp(args[0], args[1:], force=force)
    if cmd == "drift":
        _has(args, "--json")
        if len(args) != 1:
            return 2, {"error": "usage: drift <stamp.json>"}
        return improve_tools.drift(args[0])
    if cmd == "branch-scope":
        _has(args, "--json")
        base = None
        if "--base" in args:
            i = args.index("--base")
            if i + 1 >= len(args):
                return 2, {"error": "branch-scope: --base needs a REF"}
            base = _take(args, i)
        if len(args) != 1:
            return 2, {"error": "usage: branch-scope <repo> [--base REF]"}
        return improve_tools.branch_scope(args[0], base=base)
    if cmd == "rejected":
        _has(args, "--json")
        project = None
        if "--project" in args:
            i = args.index("--project")
            if i + 1 >= len(args):
                return 2, {"error": "rejected: --project needs a SLUG"}
            project = _take(args, i)
        store = None
        if "--store" in args:
            i = args.index("--store")
            if i + 1 >= len(args):
                return 2, {"error": "rejected: --store needs a PATH"}
            store = _take(args, i)
        if not args:
            return 2, {"error": "usage: rejected add|list|check ..."}
        op, rest = args[0], args[1:]
        if op == "add":
            if len(rest) != 2:
                return 2, {"error": 'usage: rejected add "<item>" '
                                    '"<reason>" [--project SLUG]'}
            return improve_tools.rejected("add", item=rest[0],
                                          reason=rest[1],
                                          project=project, store=store)
        if op == "list":
            if rest:
                return 2, {"error": "usage: rejected list [--project SLUG]"}
            return improve_tools.rejected("list", project=project,
                                          store=store)
        if op == "check":
            if len(rest) != 1:
                return 2, {"error": 'usage: rejected check "<text>" '
                                    "[--project SLUG]"}
            return improve_tools.rejected("check", item=rest[0],
                                          project=project, store=store)
        return 2, {"error": f"rejected: unknown op: {op}"}
    if cmd == "snapshot":
        _has(args, "--json")
        force = _has(args, "--force")
        if len(args) != 2:
            return 2, {"error": "usage: snapshot <target> <out.json> "
                                "[--force]"}
        return hallmark_tools.snapshot(args[0], args[1], force=force)
    if cmd == "kept":
        _has(args, "--json")
        dropped = []
        while "--dropped" in args:
            i = args.index("--dropped")
            if i + 1 >= len(args):
                return 2, {"error": "kept: --dropped needs an ITEM"}
            dropped.append(_take(args, i))
        if len(args) != 2:
            return 2, {"error": "usage: kept <before.json> <target> "
                                "[--dropped ITEM ...]"}
        return hallmark_tools.kept(args[0], args[1], dropped=dropped)
    if cmd == "words":
        _has(args, "--json")
        surface = "web"
        if "--surface" in args:
            i = args.index("--surface")
            if i + 1 >= len(args):
                return 2, {"error": "words: --surface needs a value"}
            surface = _take(args, i)
        budget = None
        if "--budget" in args:
            i = args.index("--budget")
            if i + 1 >= len(args):
                return 2, {"error": "words: --budget needs N"}
            budget = _take(args, i)
        if len(args) != 1:
            return 2, {"error": "usage: words <target> [--surface S] "
                                "[--budget N]"}
        return hallmark_tools.words(args[0], surface=surface,
                                    budget=budget)
    if cmd == "gatecheck":
        _has(args, "--json")
        surface = "web"
        if "--surface" in args:
            i = args.index("--surface")
            if i + 1 >= len(args):
                return 2, {"error": "gatecheck: --surface needs a value"}
            surface = _take(args, i)
        stage = None
        if "--stage" in args:
            i = args.index("--stage")
            if i + 1 >= len(args):
                return 2, {"error": "gatecheck: --stage needs a value"}
            stage = _take(args, i)
        stamp_path = None
        if "--stamp" in args:
            i = args.index("--stamp")
            if i + 1 >= len(args):
                return 2, {"error": "gatecheck: --stamp needs a PATH"}
            stamp_path = _take(args, i)
        if len(args) != 1:
            return 2, {"error": "usage: gatecheck <target> "
                                "[--surface S] [--stage hero] "
                                "[--stamp PATH]"}
        return hallmark_tools.gatecheck(args[0], surface=surface,
                                        stage=stage,
                                        stamp_path=stamp_path)
    if cmd == "deal":
        _has(args, "--json")
        log = None
        if "--log" in args:
            i = args.index("--log")
            if i + 1 >= len(args):
                return 2, {"error": "deal: --log needs a PATH"}
            log = _take(args, i)
        prompt = ""
        if "--prompt" in args:
            i = args.index("--prompt")
            if i + 1 >= len(args):
                return 2, {"error": "deal: --prompt needs TEXT"}
            prompt = _take(args, i)
        if len(args) != 1:
            return 2, {"error": "usage: deal <themes-dir> [--log PATH] "
                                "[--prompt TEXT]"}
        return hallmark_tools.deal(args[0], log_path=log, prompt=prompt)
    if cmd == "rotation":
        _has(args, "--json")
        log = None
        if "--log" in args:
            i = args.index("--log")
            if i + 1 >= len(args):
                return 2, {"error": "rotation: --log needs a PATH"}
            log = _take(args, i)
        entry = {}
        for axis in hallmark_tools.AXES:
            flag = f"--{axis}"
            if flag in args:
                i = args.index(flag)
                if i + 1 >= len(args):
                    return 2, {"error": f"rotation: {flag} needs TEXT"}
                entry[axis] = _take(args, i)
        waived = None
        if "--waived" in args:
            i = args.index("--waived")
            if i + 1 >= len(args):
                return 2, {"error": "rotation: --waived needs a GATE"}
            waived = _take(args, i)
        if not log or not args:
            return 2, {"error": "usage: rotation add|check|list "
                                "--log PATH [--theme T --shape S "
                                "--hero H --nav N --footer F "
                                "--signature X] [--waived GATE]"}
        if waived:
            entry["waived"] = waived
        return hallmark_tools.rotation(args[0], log, entry=entry or None)
    if cmd == "brief":
        _has(args, "--json")
        force = _has(args, "--force")
        opts = {}
        for key in ("surface", "job", "shape", "theme", "signature",
                    "real", "pictures", "absent", "critique",
                    "theme-file"):
            flag = f"--{key}"
            if flag in args:
                i = args.index(flag)
                if i + 1 >= len(args):
                    return 2, {"error": f"brief: {flag} needs TEXT"}
                opts[key] = _take(args, i)
        waivers = []
        while "--waive" in args:
            i = args.index("--waive")
            if i + 1 >= len(args):
                return 2, {"error": "brief: --waive needs TEXT"}
            waivers.append(_take(args, i))
        if len(args) != 1:
            return 2, {"error": "usage: brief <out-stamp> --surface S "
                                "--job J --shape S --theme T "
                                "--signature X --real R --pictures P "
                                "--absent A [--critique 'P5 H4 ...'] "
                                "[--theme-file PATH] [--waive TEXT] "
                                "[--force]"}
        return hallmark_tools.brief(
            args[0], surface=opts.get("surface", ""), job=opts.get("job", ""),
            shape=opts.get("shape", ""), theme=opts.get("theme", ""),
            signature=opts.get("signature", ""), real=opts.get("real", ""),
            pictures=opts.get("pictures", ""),
            absent=opts.get("absent", ""),
            critique=opts.get("critique", ""),
            theme_file=opts.get("theme-file"), waivers=waivers,
            force=force)
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
