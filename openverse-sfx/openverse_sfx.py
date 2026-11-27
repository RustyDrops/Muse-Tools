#!/usr/bin/env python3
"""Find, download and credit free sound effects from Openverse.

Stdlib only. No API key, no account. Searches the live Openverse API,
prefers CC0 (public domain, no attribution legally required), downloads
the files, and writes a CREDITS.md with the exact license and source for
every sound, so a video or a game can ship with its paperwork done.

Usage:
  python3 openverse_sfx.py search "bubble pop" --license cc0
  python3 openverse_sfx.py get "bubble pop" --out sounds/ --count 3
  python3 openverse_sfx.py get "keyboard clicks" --out sounds/ --license any

Licenses: cc0 is the safe default. "by" (CC BY) sounds are fine too, but
they legally require the credit line this tool writes into CREDITS.md.
Never ship a sound whose license you have not read on its detail record.
"""
import argparse
import json
import pathlib
import sys
import urllib.parse
import urllib.request

API = "https://api.openverse.org/v1/audio/"
UA = {"User-Agent": "openverse-sfx/1.0 (Muse-Tools)"}


def api_get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def search(query, license_filter="cc0", page_size=10):
    params = {"q": query, "page_size": page_size}
    if license_filter != "any":
        params["license"] = license_filter
    return api_get(API + "?" + urllib.parse.urlencode(params)).get("results", [])


def slug(text):
    keep = [c if c.isalnum() else "-" for c in text.lower()]
    return "".join(keep).strip("-")[:48] or "sound"


def credit_line(item):
    lic = (item.get("license") or "").upper()
    ver = item.get("license_version") or ""
    return (f'"{item.get("title")}" by {item.get("creator")} - '
            f'{lic} {ver} - {item.get("license_url")} - '
            f'source: {item.get("foreign_landing_url")}')


def cmd_search(args):
    for item in search(args.query, args.license):
        dur = (item.get("duration") or 0) / 1000
        print(f'{item.get("title")} | {item.get("creator")} | '
              f'{item.get("license")} {item.get("license_version")} | '
              f'{dur:.2f}s | {item.get("foreign_landing_url")}')
    return 0


def cmd_get(args):
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    picked = search(args.query, args.license)[: args.count]
    if not picked:
        print("No results. Try broader words, or --license any.")
        return 1
    credits = []
    for i, item in enumerate(picked, 1):
        detail = api_get(f'{API}{item["id"]}/')
        ext = detail.get("filetype") or "mp3"
        name = f'{i:02d}-{slug(detail.get("title", "sound"))}.{ext}'
        req = urllib.request.Request(detail["url"],
                                     headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
        (out / name).write_bytes(data)
        line = credit_line(detail)
        credits.append(line)
        print(f'saved {name} ({len(data)} bytes) - {line}')
    cred_path = out / "CREDITS.md"
    old = cred_path.read_text() if cred_path.exists() else "# Sound credits\n"
    cred_path.write_text(old.rstrip() + "\n" + "\n".join(
        f"- {c}" for c in credits) + "\n")
    print(f"credits written to {cred_path}")
    return 0


def main(argv):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("search", "get"):
        sp = sub.add_parser(name)
        sp.add_argument("query")
        sp.add_argument("--license", default="cc0",
                        help="cc0 (default), by, by-sa, or any")
        if name == "get":
            sp.add_argument("--out", default="sounds")
            sp.add_argument("--count", type=int, default=1)
    args = p.parse_args(argv)
    return cmd_search(args) if args.cmd == "search" else cmd_get(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
