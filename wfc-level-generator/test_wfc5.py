"""Production exam for wfc5, as an automated suite. Run:
    python test_wfc5.py
Covers T1 reliability, T2 determinism, T3 stress matrix, T4 path quality,
T5 export round trips, T6 refusal behaviour, T7 clean input errors, timing.
Exits nonzero if anything fails.
"""
import json, os, subprocess, sys, tempfile, time
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "wfc5.py")
sys.path.insert(0, HERE)
import wfc5

RESULTS = []
def check(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")

def dotted_count(grid, feats):
    walk = set()
    for c in feats["clearings"]:
        cx, cy, r = c["x"], c["y"], c.get("radius", 2)
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dx * dx + dy * dy <= r * r + 1:
                    walk.add((cx + dx, cy + dy))
    h, w = len(grid), len(grid[0])
    for y in range(h):
        for x in range(w):
            if grid[y][x] == "P":
                walk.add((x, y))
    n = 0
    for (x, y) in list(walk):
        if grid[y][x] == "P" and not any((x + dx, y + dy) in walk for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            n += 1
    return n

# ---------- T3 + T4: stress matrix through the module API ----------
matrix = [
    (16, 16, 0.20, 0.60), (24, 24, 0.20, 0.60), (32, 32, 0.20, 0.60),
    (48, 32, 0.20, 0.60), (32, 48, 0.20, 0.60),
    (32, 32, 0.12, 0.55), (32, 32, 0.28, 0.68), (32, 32, 0.12, 0.68), (32, 32, 0.28, 0.55),
    (64, 64, 0.20, 0.60),
]
matrix_passers = {}
for (w, h, water, forest) in matrix:
    wfc5.W, wfc5.H = w, h
    cap = 60 if w * h > 2048 else 150
    t0 = time.time()
    passers, attempts, last_fail = wfc5.generate_passer(0, cap, water, forest, want=1)
    dt = round(time.time() - t0, 1)
    ok = bool(passers) and passers[0]["passed"] and not passers[0]["failures"]
    check(f"T3 matrix {w}x{h} water={water} forest={forest}", ok,
          f"attempts={attempts} in {dt}s" if ok else f"no passer in {cap}: {last_fail}")
    if ok:
        matrix_passers[(w, h, water, forest)] = passers[0]
        d = dotted_count(passers[0]["grid"], passers[0]["feats"])
        check(f"T4 path solid {w}x{h} water={water} forest={forest}", d == 0, f"dotted cells={d}")

# ---------- T5: export round trips on the 32 default passer ----------
p = matrix_passers.get((32, 32, 0.20, 0.60))
if p:
    wfc5.W, wfc5.H = 32, 32
    with tempfile.TemporaryDirectory() as td:
        prefix = os.path.join(td, "m")
        wfc5.export_map(p["grid"], p["feats"], p["sb"], prefix, {"seed_used": p["seed"]})
        dj = json.load(open(prefix + ".json"))
        same_json = dj["grid"] == ["".join(r) for r in p["grid"]]
        check("T5 JSON parse-back exact", same_json and dj["version"] == wfc5.VERSION)
        root = ET.parse(prefix + ".tmx").getroot()
        csv = root.find("./layer/data").text.strip()
        ids = [int(v) for v in csv.replace("\n", "").split(",") if v.strip()]
        inv = {v: k for k, v in wfc5.TILE_IDS.items()}
        tmx_grid = ["".join(inv[ids[y * 32 + x]] for x in range(32)) for y in range(32)]
        check("T5 TMX parse-back exact", tmx_grid == ["".join(r) for r in p["grid"]])
        check("T5 tileset image written", os.path.exists(os.path.join(td, "wfc_tileset.png")))

# ---------- the suite catches a broken rule (negative control) ----------
bad_grid = [list("GGGG"), list("GWGG"), list("GGGG"), list("GGGG")]
wfc5.W, wfc5.H = 4, 4
sb_bad = wfc5.scoreboard(["".join(r) for r in bad_grid])
check("negative control: water touching grass is caught",
      sb_bad["water_grass_adjacencies"] > 0 and bool(wfc5.gate_failures(sb_bad, True)))

# ---------- CLI behaviour in temp dirs ----------
def run_cli(args, cwd, env_extra=None):
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    return subprocess.run([sys.executable, TOOL] + args, cwd=cwd, env=env,
                          capture_output=True, text=True, timeout=300)

# T2 determinism across processes and hash seeds
grids = []
for hs in ("0", "1"):
    with tempfile.TemporaryDirectory() as td:
        r = run_cli(["--seed", "3", "--out", "m"], td, {"PYTHONHASHSEED": hs})
        assert r.returncode == 0, r.stderr[-500:]
        grids.append(open(os.path.join(td, "m.txt")).read())
check("T2 same seed, two processes, two hash seeds, identical grid", grids[0] == grids[1])

# T1 reliability: 10 single-seed runs, every one must ship a verified passer
t1_ok, t1_detail = True, ""
for s in range(10):
    with tempfile.TemporaryDirectory() as td:
        r = run_cli(["--seed", str(s * 7), "--out", "m"], td)
        if r.returncode != 0:
            t1_ok, t1_detail = False, f"seed {s * 7} exited {r.returncode}: {r.stderr[-200:]}"
            break
        v = run_cli(["--verify", "m.json"], td)
        if v.returncode != 0:
            t1_ok, t1_detail = False, f"seed {s * 7} shipped map failed verify"
            break
check("T1 reliability 10 of 10 single-seed runs ship verified maps", t1_ok, t1_detail)

# T6 refusal: a known failing seed with a 1-attempt cap writes nothing, exit 3
wfc5.W, wfc5.H = 32, 32
fail_seed = None
for s in range(60):
    r0 = wfc5.generate_one(s, 0.20, 0.60)
    if r0 is not None and not r0["passed"]:
        fail_seed = s
        break
if fail_seed is None:
    check("T6 refusal", False, "no failing seed found in 0..59 to test with")
else:
    with tempfile.TemporaryDirectory() as td:
        r = run_cli(["--seed", str(fail_seed), "--max-attempts", "1", "--out", "m"], td)
        wrote = any(f.startswith("m.") for f in os.listdir(td))
        check("T6 refusal: failing seed, cap 1, exit 3, no files",
              r.returncode == 3 and not wrote, f"seed={fail_seed} exit={r.returncode} wrote={wrote}")

# T7 clean errors
bad_calls = [
    ["--water", "24"], ["--water", "-1"], ["--forest", "0.9"], ["--forest", "0.2"],
    ["--size", "3"], ["--size", "5000"], ["--seed", "-2"], ["--out", "/no-such-dir-xyz/m"],
    ["--max-attempts", "0"],
]
t7_ok, t7_detail = True, ""
for bc in bad_calls:
    with tempfile.TemporaryDirectory() as td:
        r = run_cli(bc, td)
        if r.returncode != 2 or "error:" not in r.stderr or "Traceback" in r.stderr:
            t7_ok, t7_detail = False, f"{bc} -> exit {r.returncode}, stderr: {r.stderr[-160:]}"
            break
check("T7 bad inputs: exit 2, clean error, no traceback", t7_ok, t7_detail)

# timing: one default 32x32 shop, no sheet, under 30s
with tempfile.TemporaryDirectory() as td:
    t0 = time.time()
    r = run_cli(["--out", "m"], td)
    dt = time.time() - t0
    check("timing: default 32x32 shop under 30s", r.returncode == 0 and dt < 30, f"{dt:.1f}s exit={r.returncode}")

fails = [n for n, ok, _ in RESULTS if not ok]
print(f"\n{len(RESULTS) - len(fails)}/{len(RESULTS)} checks passed")
if fails:
    print("FAILED:", "; ".join(fails))
    sys.exit(1)
print("ALL PASS")
