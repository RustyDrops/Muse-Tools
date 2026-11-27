#!/usr/bin/env python3
"""Scan a Kenney GLB folder and write a manifest with real world fit targets.

Usage:
    python3 make-manifest.py <glb-folder> <names,comma,separated,or,ALL> <out.json>

Each entry gets its raw bounds measured straight from the GLB accessors
(node transforms in Kenney packs are identity for these models, verified
against Three.js Box3 in the rank 2 test) plus a fit target from TARGETS.
Unknown names get mode "none": add a real world size for them in TARGETS
instead of hand-tuning scale in scene code.
"""
import json
import struct
import sys
from pathlib import Path

# name -> (mode, meters, what that size is in the real world)
TARGETS = {
    "rugRectangle": ("width", 3.2, "living room rug, long side"),
    "loungeSofa": ("height", 0.85, "sofa back height"),
    "tableCoffee": ("height", 0.45, "coffee table height"),
    "bookcaseOpen": ("height", 1.80, "tall bookcase"),
    "cabinetTelevision": ("height", 0.62, "TV stand height"),
    "televisionModern": ("height", 0.60, "TV screen height, sits on stand"),
    "bedSingle": ("height", 0.55, "single bed frame plus mattress"),
    "desk": ("height", 0.75, "desk height"),
    "chairDesk": ("height", 0.92, "desk chair back height"),
    "laptop": ("width", 0.34, "laptop width, sits on desk"),
    "pottedPlant": ("height", 0.75, "floor plant"),
    "lampSquareFloor": ("height", 1.55, "floor lamp"),
    "books": ("width", 0.28, "small book stack, sits on a surface"),
    "chair": ("height", 0.90, "dining chair back height"),
    "table": ("height", 0.75, "dining table height"),
}


def glb_bounds(path):
    data = Path(path).read_bytes()
    assert data[:4] == b"glTF", f"not a GLB: {path}"
    clen, _ = struct.unpack("<I4s", data[12:20])
    js = json.loads(data[20:20 + clen])
    pos = set()
    for mesh in js.get("meshes", []):
        for prim in mesh["primitives"]:
            pos.add(prim["attributes"]["POSITION"])
    mins = [float("inf")] * 3
    maxs = [float("-inf")] * 3
    for i in pos:
        acc = js["accessors"][i]
        for k in range(3):
            mins[k] = min(mins[k], acc["min"][k])
            maxs[k] = max(maxs[k], acc["max"][k])
    return [round(maxs[k] - mins[k], 4) for k in range(3)]


def main():
    folder, names_arg, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
    files = {p.stem: p for p in folder.glob("*.glb")}
    names = sorted(files) if names_arg == "ALL" else names_arg.split(",")
    entries = []
    for name in names:
        if name not in files:
            sys.exit(f"missing GLB for {name} in {folder}")
        mode, meters, note = TARGETS.get(name, ("none", None, "no target yet"))
        entries.append({
            "name": name,
            "file": f"assets/{name}.glb",
            "rawSize": glb_bounds(files[name]),
            "fit": {"mode": mode, "meters": meters},
            "note": note,
        })
    out.write_text(json.dumps(entries, indent=2))
    print(f"wrote {out} with {len(entries)} entries")
    for e in entries:
        print(f"  {e['name']}: raw {e['rawSize']} -> {e['fit']['mode']} {e['fit']['meters']}")


if __name__ == "__main__":
    main()
