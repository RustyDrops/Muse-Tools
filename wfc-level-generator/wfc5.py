"""WFC v3: layout first, WFC second, guided by Elephant-Goldfish + swarm input.

EG verdict on v2: sand became a maze (largest terrain, one connected network),
2x2 patterns cannot see feature scale (roundness, spacing, shore thickness),
and region stats were counted on different bases for v1 and v2.
Goldfish verdict: v1 looks like terrain, v2 looks like plumbing. Keep organic
shapes, thin beaches, clustered forest, add texture.
Swarm levers used: 1 guidance field, 2 pre-seeded skeletons, 5 shore
discipline, 7 forest as clustered layer, 3 richer rendering, 12 seed search
with a beauty score. EG fixes used: sand only next to water, fixed scoreboard,
forest as decoration layer, deterministic ordering, seed shop.

Pipeline:
  A. Layout: fractal value-noise elevation + moisture. Water basins from
     elevation, sand as the 1 cell ring around water, forest from moisture
     clusters at least 2 cells from shore. This sets composition.
  B. Guided WFC: terrain cells collapse under hard adjacency rules
     (water only touches water/sand; forest never touches water) with
     weights strongly biased to the layout. WFC repairs layout cells that
     would break the rules and varies the rest. Guarantees hold by solver.
  C. Seed shop: many seeds scored on one fixed scoreboard, best keeper wins.
  D. Render: 4x subcell grid, rule-safe majority smoothing rounds the
     shorelines, jittered tree dots, subtle shade variation.
"""
import random, json, time, math, sys
from collections import deque, Counter
from PIL import Image, ImageDraw

W = H = 32
TERRAINS = "WGSFP"
ALLOWED = {  # symmetric adjacency rules, the hard guarantee
    "W": set("WS"),
    "S": set("WGSFP"),
    "G": set("GSFP"),
    "F": set("GSFP"),
    "P": set("GSFP"),  # dirt path: land only, never water (checked explicitly too)
}

# ---------- A. layout ----------
def value_noise(rng, cell_size, w=None, h=None):
    w = W if w is None else w
    h = H if h is None else h
    gw, gh = w // cell_size + 2, h // cell_size + 2
    grid = [[rng.random() for _ in range(gw)] for _ in range(gh)]
    out = [[0.0] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            gx, gy = x / cell_size, y / cell_size
            x0, y0 = int(gx), int(gy)
            fx, fy = gx - x0, gy - y0
            sx, sy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
            v = (grid[y0][x0] * (1 - sx) * (1 - sy) + grid[y0][x0 + 1] * sx * (1 - sy)
                 + grid[y0 + 1][x0] * (1 - sx) * sy + grid[y0 + 1][x0 + 1] * sx * sy)
            out[y][x] = v
    return out

def fractal(rng, w=None, h=None):
    w = W if w is None else w
    h = H if h is None else h
    a = value_noise(rng, 16, w, h)
    b = value_noise(rng, 8, w, h)
    c = value_noise(rng, 4, w, h)
    return [[0.55 * a[y][x] + 0.30 * b[y][x] + 0.15 * c[y][x] for x in range(w)] for y in range(h)]

def smooth3(g):
    out = [[0.0] * W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            vals = [g[yy][xx] for yy in (y - 1, y, y + 1) if 0 <= yy < H
                    for xx in (x - 1, x, x + 1) if 0 <= xx < W]
            out[y][x] = sum(vals) / len(vals)
    return out

def build_layout(seed, water_share=0.20, forest_moist=0.60):
    rng = random.Random(10_000 + seed)
    elev = fractal(rng)
    moist = fractal(rng)
    if max(W, H) >= 48:
        # larger grids carry finer noise detail; extra smoothing keeps lake
        # and forest shapes at the visual scale the gates were fitted on
        elev = smooth3(smooth3(smooth3(elev)))
        moist = smooth3(smooth3(moist))
    # border lift: basins form in the interior, not clipped by the map edge
    for y in range(H):
        for x in range(W):
            d = min(x, y, W - 1 - x, H - 1 - y)
            if d < 4:
                elev[y][x] += 0.22 * (1 - d / 4)
    # water: lowest elevation, threshold tuned for roughly 20 percent
    flat = sorted(elev[y][x] for y in range(H) for x in range(W))
    t_water = flat[int(water_share * len(flat))]
    lay = [["G"] * W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            if elev[y][x] <= t_water:
                lay[y][x] = "W"
    # drop pond-sized water regions, they render as boxy sand boxes
    min_lake = max(8, int(0.03 * W * H))
    for cells in components(lay, "W"):
        if len(cells) < min_lake:
            for (x, y) in cells:
                lay[y][x] = "G"
    # sand: exactly the 1 cell ring around water (8-neighbourhood)
    for y in range(H):
        for x in range(W):
            if lay[y][x] == "W":
                continue
            near = any(0 <= x + dx < W and 0 <= y + dy < H and lay[y + dy][x + dx] == "W"
                       for dy in (-1, 0, 1) for dx in (-1, 0, 1))
            if near:
                lay[y][x] = "S"
    if max(W, H) >= 48:
        # second shore ring at large sizes: ring perimeter grows with the
        # square root of area, so a 1 cell ring under-delivers sand at 64
        ring2 = [(x, y) for y in range(H) for x in range(W) if lay[y][x] == "G"
                 and any(0 <= x + dx < W and 0 <= y + dy < H and lay[y + dy][x + dx] == "S"
                         for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
        for (x, y) in ring2:
            lay[y][x] = "S"
    # forest: moisture clusters, at least 2 cells (Chebyshev) from water,
    # small target clusters removed
    for y in range(H):
        for x in range(W):
            if lay[y][x] != "G" or moist[y][x] < forest_moist:
                continue
            far = all(not (0 <= x + dx < W and 0 <= y + dy < H) or lay[y + dy][x + dx] != "W"
                      for dy in range(-2, 3) for dx in range(-2, 3))
            far = far and 2 <= x < W - 2 and 2 <= y < H - 2
            if far:
                lay[y][x] = "F"
    lay = remove_small(lay, "F", 4)
    for _ in range(3 if max(W, H) >= 48 else 2):
        thin = [(x, y) for y in range(H) for x in range(W) if lay[y][x] == "F"
                and sum(1 for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]
                        if 0 <= x + dx < W and 0 <= y + dy < H and lay[y + dy][x + dx] == "F") < 2]
        for (x, y) in thin:
            lay[y][x] = "G"
    lay = remove_small(lay, "F", max(6, int(0.004 * W * H)))
    return lay, elev, moist

def components(lay, ch):
    seen = [[False] * W for _ in range(H)]
    comps = []
    for y in range(H):
        for x in range(W):
            if lay[y][x] == ch and not seen[y][x]:
                stack, cells = [(x, y)], []
                seen[y][x] = True
                while stack:
                    cx, cy = stack.pop(); cells.append((cx, cy))
                    for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < W and 0 <= ny < H and not seen[ny][nx] and lay[ny][nx] == ch:
                            seen[ny][nx] = True; stack.append((nx, ny))
                comps.append(cells)
    return comps

def remove_small(lay, ch, min_size, fill="G"):
    lay = [row[:] for row in lay]
    for cells in components(lay, ch):
        if len(cells) < min_size:
            for (x, y) in cells:
                lay[y][x] = fill
    return lay

# ---------- B. guided WFC ----------
def solve(layout, moist, seed):
    rng = random.Random(20_000 + seed)
    # forest candidates only where moisture supports clusters
    possible = []
    for y in range(H):
        for x in range(W):
            opts = set("WGS")
            if moist[y][x] > 0.55 and 2 <= x < W - 2 and 2 <= y < H - 2:
                opts.add("F")
            possible.append(opts)
    def weight(x, y, t):
        target = layout[y][x]
        if t == target:
            # boundary cells are genuinely WFC territory: low target weight,
            # so the solver grows shore and forest edge detail itself.
            # Interior cells stay layout locked.
            boundary = any(0 <= x + dx < W and 0 <= y + dy < H and layout[y + dy][x + dx] != target
                           for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)])
            return 8.0 if boundary else 400.0
        if t == "S":
            # shore fixer only near layout water, weak inland
            near_water = target == "S" or any(
                0 <= x + dx < W and 0 <= y + dy < H and layout[y + dy][x + dx] == "W"
                for dy in (-1, 0, 1) for dx in (-1, 0, 1))
            return 3.0 if near_water else 0.1
        return 0.05
    def propagate(start):
        q = deque([start])
        while q:
            c = q.popleft()
            cx, cy = c % W, c // W
            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                nx, ny = cx + dx, cy + dy
                if not (0 <= nx < W and 0 <= ny < H):
                    continue
                n = ny * W + nx
                supported = set()
                for t in possible[c]:
                    supported |= ALLOWED[t]
                new = possible[n] & supported
                if not new:
                    return False
                if new != possible[n]:
                    possible[n] = new
                    q.append(n)
        return True
    while True:
        cand, best = None, 10 ** 9
        for i, p in enumerate(possible):
            if 1 < len(p) < best:
                best, cand = len(p), i
        if cand is None:
            break
        x, y = cand % W, cand // W
        opts = sorted(possible[cand])
        pick = rng.choices(opts, weights=[weight(x, y, t) for t in opts], k=1)[0]
        possible[cand] = {pick}
        if not propagate(cand):
            return None
    return ["".join(possible[y * W + x].pop() for x in range(W)) for y in range(H)]

def cleanup(grid):
    """Rule-safe post pass (swarm lever 8): flip orphan sand to grass, and
    flip single cell regions to a neighbour terrain, only when every
    resulting adjacency still obeys ALLOWED. Layout structure untouched."""
    grid = [list(r) for r in grid]
    def safe(x, y, t):
        return all(grid[ny][nx] in ALLOWED[t] and t in ALLOWED[grid[ny][nx]]
                   for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]
                   for nx, ny in [(x + dx, y + dy)] if 0 <= nx < W and 0 <= ny < H)
    for _ in range(6):
        changed = False
        for y in range(H):
            for x in range(W):
                if grid[y][x] == "S":
                    touches = any(0 <= x + dx < W and 0 <= y + dy < H and grid[y + dy][x + dx] == "W"
                                  for dy in (-2, -1, 0, 1, 2) for dx in (-2, -1, 0, 1, 2))
                    if not touches and safe(x, y, "G"):
                        grid[y][x] = "G"; changed = True
        singles = set()
        for ch in "WGSF":
            for cells in components(grid, ch):
                if len(cells) == 1:
                    singles.add(cells[0])
        # solver edge detail can strand 2-3 cell forest specks; clear them too
        for cells in components(grid, "F"):
            if len(cells) <= 3:
                for (x, y) in cells:
                    if safe(x, y, "G"):
                        grid[y][x] = "G"; changed = True
        for (x, y) in singles:
            neigh = Counter(grid[y + dy][x + dx] for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]
                            if 0 <= x + dx < W and 0 <= y + dy < H)
            for t, _ in neigh.most_common():
                if t != grid[y][x] and safe(x, y, t):
                    grid[y][x] = t; changed = True; break
        if not changed:
            break
    return ["".join(r) for r in grid]

# ---------- scoreboard (one fixed basis: terrain cells) ----------
def scoreboard(grid):
    counts = Counter("".join(grid))
    total = W * H
    wg = sand_orphan = 0
    for y in range(H):
        for x in range(W):
            ch = grid[y][x]
            for dx, dy in [(1, 0), (0, 1)]:
                nx, ny = x + dx, y + dy
                if nx < W and ny < H:
                    a, b = ch, grid[ny][nx]
                    if (a == "W" and b in "GF") or (b == "W" and a in "GF"):
                        wg += 1
            if ch == "S":
                touches_water = any(0 <= x + dx < W and 0 <= y + dy < H and grid[y + dy][x + dx] == "W"
                                    for dy in (-2, -1, 0, 1, 2) for dx in (-2, -1, 0, 1, 2))
                if not touches_water:
                    sand_orphan += 1
    # land connectivity: non-water cells, 4-connected (path counts as land)
    land_seen = [[False] * W for _ in range(H)]
    land_regions = 0
    for y in range(H):
        for x in range(W):
            if grid[y][x] != "W" and not land_seen[y][x]:
                land_regions += 1
                stack = [(x, y)]; land_seen[y][x] = True
                while stack:
                    cx, cy = stack.pop()
                    for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < W and 0 <= ny < H and not land_seen[ny][nx] and grid[ny][nx] != "W":
                            land_seen[ny][nx] = True; stack.append((nx, ny))
    # forest shape: per region >= 10 cells, roundness and erosion core ratio
    forest_shape = []
    for cells in components(grid, "F"):
        if len(cells) < 10:
            continue
        s = set(cells); per = 0; core = 0
        for (x, y) in cells:
            nb = [(x + dx, y + dy) for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]]
            per += sum(1 for p in nb if p not in s)
            if all(p in s for p in nb):
                core += 1
        forest_shape.append({"area": len(cells), "p2_over_a": round(per * per / len(cells), 1),
                             "core_ratio": round(core / len(cells), 2)})
    # composition: halves balance and quadrant feature presence
    def share_left(ch):
        tot = counts.get(ch, 0)
        if not tot: return 0.5
        left = sum(1 for y in range(H) for x in range(W // 2) if grid[y][x] == ch)
        return round(left / tot, 2)
    def share_top(ch):
        tot = counts.get(ch, 0)
        if not tot: return 0.5
        top = sum(1 for y in range(H // 2) for x in range(W) if grid[y][x] == ch)
        return round(top / tot, 2)
    quad_non_grass = []
    for qy in (0, H // 2):
        for qx in (0, W // 2):
            cells = [(x, y) for y in range(qy, qy + H // 2) for x in range(qx, qx + W // 2)]
            quad_non_grass.append(round(sum(1 for (x, y) in cells if grid[y][x] != "G") / len(cells), 2))
    # regions per terrain
    all_sizes, singles = [], 0
    for ch in "WGSF":
        for cells in components(grid, ch):
            all_sizes.append(len(cells))
            if len(cells) == 1:
                singles += 1
    # water roundness: perimeter squared over area, per water region >= 20
    roundness = []
    for cells in components(grid, "W"):
        if len(cells) < 20:
            continue
        s = set(cells); per = 0
        for (x, y) in cells:
            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                if (x + dx, y + dy) not in s:
                    per += 1
        roundness.append(round(per * per / len(cells), 1))
    border_forest = sum(1 for y in range(H) for x in range(W)
                        if grid[y][x] == "F" and (x < 2 or y < 2 or x >= W - 2 or y >= H - 2))
    border_water = sum(1 for y in range(H) for x in range(W)
                       if grid[y][x] == "W" and (x == 0 or y == 0 or x == W - 1 or y == H - 1))
    same = tot = 0
    for y in range(H):
        for x in range(W):
            for dx, dy in [(1, 0), (0, 1)]:
                nx, ny = x + dx, y + dy
                if nx < W and ny < H:
                    tot += 1; same += grid[y][x] == grid[ny][nx]
    return {
        "water_grass_adjacencies": wg,
        "sand_orphan_cells": sand_orphan,
        "sand_share": round(counts.get("S", 0) / total, 3),
        "water_share": round(counts.get("W", 0) / total, 3),
        "land_share": round((counts.get("G", 0) + counts.get("F", 0)) / total, 3),
        "forest_share": round(counts.get("F", 0) / total, 3),
        "regions": len(all_sizes),
        "mean_region_size": round(total / max(1, len(all_sizes)), 2),
        "single_cell_regions": singles,
        "same_neighbour_fraction": round(same / tot, 3),
        "water_roundness_P2_over_A": roundness,
        "land_regions": land_regions,
        "forest_shape": forest_shape,
        "water_left_share": share_left("W"), "water_top_share": share_top("W"),
        "forest_left_share": share_left("F"), "forest_top_share": share_top("F"),
        "quadrant_non_grass_min": min(quad_non_grass) if quad_non_grass else 0,
        "border_forest_cells": border_forest,
        "border_water_cells": border_water,
        "terrain_counts": dict(counts),
    }

def beauty(sb):
    # lower is better; hard failures handled by gates before scoring
    score = 0.0
    score += abs(sb["sand_share"] - 0.15) * 300
    score += sb["sand_orphan_cells"] * 2.0
    score += sb["single_cell_regions"] * 3.0
    score += max(0.0, 0.60 - sb["same_neighbour_fraction"]) * 200
    score += sum(max(0.0, r - 45) for r in sb["water_roundness_P2_over_A"])
    score += abs(sb["water_share"] - 0.20) * 150
    score += sb.get("border_forest_cells", 0) * 4.0
    score += sb.get("border_water_cells", 0) * 2.0
    for fs in sb.get("forest_shape", []):
        score += max(0.0, fs["p2_over_a"] - 60) * 0.5
        score += max(0.0, 0.25 - fs["core_ratio"]) * 120
    score += abs(sb.get("water_left_share", 0.5) - 0.5) * 60
    score += abs(sb.get("forest_left_share", 0.5) - 0.5) * 40
    score += max(0.0, 0.05 - sb.get("quadrant_non_grass_min", 0)) * 300
    return round(score, 1)

def gates_v4(sb):
    return (gates(sb)
        and sb.get("land_regions", 99) == 1
        and all(fs["p2_over_a"] < 90 and fs["core_ratio"] >= 0.15 for fs in sb.get("forest_shape", []))
        and 0.15 <= sb.get("water_left_share", 0) <= 0.85
        and 0.15 <= sb.get("water_top_share", 0) <= 0.85
        and sb.get("quadrant_non_grass_min", 0) >= 0.04)

def gates(sb):
    return (
        sb["water_grass_adjacencies"] == 0
        and 0.08 <= sb["sand_share"] <= 0.25
        and sb["sand_orphan_cells"] <= 10
        and 0.10 <= sb["water_share"] <= 0.35
        and sb["land_share"] >= 0.45
        and sb["single_cell_regions"] <= 25
        and sb["mean_region_size"] >= 8
        and all(r < 60 for r in sb["water_roundness_P2_over_A"])
    )


# ---------- features layer: clearings + dirt path ----------
import heapq
def add_features(grid, seed):
    """Stamp 3 clearings (spawn, camp, objective) on land away from shores,
    then carve an A* dirt path between them over grass/forest only.
    Path never touches water (verified in check_features)."""
    rng = random.Random(30_000 + seed)
    grid = [list(r) for r in grid]
    def dist_to_water(x, y):
        d = 99
        for yy in range(H):
            for xx in range(W):
                if grid[yy][xx] == "W":
                    d = min(d, max(abs(xx - x), abs(yy - y)))
        return d
    band = max(2, W // 8)
    cands = [(x, y) for y in range(band, H - band) for x in range(band, W - band)
             if grid[y][x] in "GF" and dist_to_water(x, y) >= max(3, W // 8)]
    if len(cands) < 3:
        return None
    centers = [cands[rng.randrange(len(cands))]]
    while len(centers) < 3:
        best, bestd = None, -1
        for c in cands:
            d = min(abs(c[0] - o[0]) + abs(c[1] - o[1]) for o in centers)
            if d > bestd:
                bestd, best = d, c
        if bestd < max(8, W // 3):
            return None
        centers.append(best)
    names = ["spawn", "camp", "objective"]
    crad = 2 if W >= 24 else 1
    # stamp clearing discs to grass, from grass/forest only
    for (cx, cy) in centers:
        for dy in range(-crad, crad + 1):
            for dx in range(-crad, crad + 1):
                if dx * dx + dy * dy <= crad * crad + 1:
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < W and 0 <= ny < H and grid[ny][nx] in "GF":
                        grid[ny][nx] = "G"
    wander = fractal(random.Random(40_000 + seed))
    def astar(a, b):
        open_h = [(0, a)]; came = {a: None}; cost = {a: 0.0}
        while open_h:
            _, cur = heapq.heappop(open_h)
            if cur == b:
                path = []
                while cur is not None:
                    path.append(cur); cur = came[cur]
                return path[::-1]
            cx, cy = cur
            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                nx, ny = cx + dx, cy + dy
                if not (0 <= nx < W and 0 <= ny < H) or grid[ny][nx] not in "GF":
                    continue
                step = (1.0 if grid[ny][nx] == "G" else 2.5) + wander[ny][nx] * 2.2
                if nx < 3 or ny < 3 or nx >= W - 3 or ny >= H - 3:
                    step += 2.5
                if any(0 <= nx + dx < W and 0 <= ny + dy < H and grid[ny + dy][nx + dx] in "WS"
                       for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]):
                    step += 0.8
                nc = cost[cur] + step
                if (nx, ny) not in cost or nc < cost[(nx, ny)]:
                    cost[(nx, ny)] = nc; came[(nx, ny)] = cur
                    heapq.heappush(open_h, (nc + abs(nx - b[0]) + abs(ny - b[1]), (nx, ny)))
        return None
    path_cells = []
    for i in range(2):
        p = astar(centers[i], centers[i + 1])
        if p is None:
            return None
        path_cells += p[1:-1]
    center_set = set(centers)
    for (x, y) in path_cells:
        if (x, y) not in center_set:
            grid[y][x] = "P"
    # wiggle pass: shift interior path cells sideways where the chain stays
    # connected (8-dir) and the new cell is land not next to water
    chain = []
    seen_pc = set()
    for (x, y) in path_cells:
        if (x, y) not in seen_pc:
            seen_pc.add((x, y)); chain.append((x, y))
    def near_water(x, y):
        return any(0 <= x + dx < W and 0 <= y + dy < H and grid[y + dy][x + dx] == "W"
                   for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)])
    for _ in range(3):
        for i in range(1, len(chain) - 1):
            (px, py), (cx, cy), (nx, ny) = chain[i - 1], chain[i], chain[i + 1]
            if (cx, cy) in center_set or rng.random() < 0.4:
                continue
            for sx, sy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                tx, ty = cx + sx, cy + sy
                if not (0 <= tx < W and 0 <= ty < H) or grid[ty][tx] not in "GF":
                    continue
                if near_water(tx, ty):
                    continue
                if max(abs(tx - px), abs(ty - py)) <= 1 and max(abs(tx - nx), abs(ty - ny)) <= 1:
                    grid[cy][cx] = "G"
                    grid[ty][tx] = "P"
                    chain[i] = (tx, ty)
                    break
    # stitch pass: bridge diagonal-only joints with a corner path cell so
    # the whole route is 4-connected (no dotted trail)
    def walk_cells():
        s = set()
        for (cx, cy) in centers:
            for dy in range(-crad, crad + 1):
                for dx in range(-crad, crad + 1):
                    if dx * dx + dy * dy <= crad * crad + 1 and 0 <= cx + dx < W and 0 <= cy + dy < H:
                        s.add((cx + dx, cy + dy))
        for yy in range(H):
            for xx in range(W):
                if grid[yy][xx] == "P":
                    s.add((xx, yy))
        return s
    for _ in range(64):
        walk = walk_cells()
        comp = {}
        cid = 0
        for c in walk:
            if c in comp:
                continue
            cid += 1
            stack = [c]; comp[c] = cid
            while stack:
                px, py = stack.pop()
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    n = (px + dx, py + dy)
                    if n in walk and n not in comp:
                        comp[n] = cid; stack.append(n)
        main_cid = comp.get(centers[0])
        if all(comp.get(c) == main_cid for c in walk):
            break
        bridged = False
        for (x, y) in sorted(walk):
            if comp[(x, y)] == main_cid:
                continue
            for dx, dy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                n = (x + dx, y + dy)
                if n in walk and comp.get(n) == main_cid:
                    for (kx, ky) in ((n[0], y), (x, n[1])):
                        if 0 <= kx < W and 0 <= ky < H and grid[ky][kx] in "GF" and not near_water(kx, ky):
                            grid[ky][kx] = "P"
                            bridged = True
                            break
                if bridged:
                    break
            if bridged:
                break
        if not bridged:
            break
    feats = {"clearings": [{"name": names[i], "x": centers[i][0], "y": centers[i][1], "radius": crad}
                           for i in range(3)],
             "path_cells": len([1 for y in range(H) for x in range(W) if grid[y][x] == "P"])}
    return ["".join(r) for r in grid], feats

def check_features(grid, feats):
    if feats is None:
        return False
    # path never next to water (4-dir)
    for y in range(H):
        for x in range(W):
            if grid[y][x] == "P":
                for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < W and 0 <= ny < H and grid[ny][nx] == "W":
                        return False
    # path quality: not a perimeter frame, no long straight runs
    pcells = [(x, y) for y in range(H) for x in range(W) if grid[y][x] == "P"]
    if pcells:
        border = sum(1 for (x, y) in pcells if x < 3 or y < 3 or x >= W - 3 or y >= H - 3)
        if border / len(pcells) > 0.35:
            return False
        def max_run(vals):
            best = run = 1
            for a, b in zip(vals, vals[1:]):
                run = run + 1 if b == a + 1 else 1
                best = max(best, run)
            return best
        run_cap = max(8, W // 2)
        for y in range(H):
            xs = sorted(x for x in range(W) if grid[y][x] == "P")
            if xs and max_run(xs) > run_cap:
                return False
        for x in range(W):
            ys = sorted(y for y in range(H) if grid[y][x] == "P")
            if ys and max_run(ys) > run_cap:
                return False
    # route connectivity: BFS from spawn over path + clearing discs + land
    centers = [(c["x"], c["y"]) for c in feats["clearings"]]
    walk = set()
    for c in feats["clearings"]:
        cx, cy, crad = c["x"], c["y"], c.get("radius", 2)
        for dy in range(-crad, crad + 1):
            for dx in range(-crad, crad + 1):
                if dx * dx + dy * dy <= crad * crad + 1 and 0 <= cx + dx < W and 0 <= cy + dy < H:
                    walk.add((cx + dx, cy + dy))
    walk |= {(x, y) for y in range(H) for x in range(W) if grid[y][x] == "P"}
    # dotted check: every path cell needs a 4-neighbour on the route
    for (x, y) in pcells:
        if not any((x + dx, y + dy) in walk for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            return False
    # route connectivity: strict 4-direction BFS from spawn
    seen = {centers[0]}; stack = [centers[0]]
    while stack:
        cx, cy = stack.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (cx + dx, cy + dy)
            if n in walk and n not in seen:
                seen.add(n); stack.append(n)
    return all(c in seen for c in centers)

# ---------- D. render ----------
BASE = {"G": (101, 171, 99), "W": (62, 124, 208), "S": (232, 213, 158), "F": (74, 138, 78), "P": (178, 143, 97)}
WATER_DEPTH = {1: (116, 176, 230), 2: (74, 140, 216), 3: (52, 112, 198)}
def render(grid, path, cell=16, sub=4, feats=None):
    sw, sh = W * sub, H * sub
    sg = [[grid[y // sub][x // sub] for x in range(sw)] for y in range(sh)]
    for _ in range(2):
        nxt = [row[:] for row in sg]
        for y in range(sh):
            for x in range(sw):
                cnt = Counter()
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < sw and 0 <= ny < sh and (dx or dy):
                            cnt[sg[ny][nx]] += 1
                top, n = cnt.most_common(1)[0]
                if top != sg[y][x] and n >= 5:
                    ok = True
                    for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < sw and 0 <= ny < sh:
                            other = nxt[ny][nx] if (ny, nx) != (y, x) else top
                            if top not in ALLOWED[other]:
                                ok = False
                    if ok:
                        nxt[y][x] = top
        sg = nxt
    # water depth per logical cell: BFS distance to nearest non-water
    depth = [[0] * W for _ in range(H)]
    dq = deque()
    for y in range(H):
        for x in range(W):
            if grid[y][x] != "W":
                depth[y][x] = 0; dq.append((x, y))
    while dq:
        cx, cy = dq.popleft()
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < W and 0 <= ny < H and depth[ny][nx] == 0 and grid[ny][nx] == "W":
                depth[ny][nx] = depth[cy][cx] + 1; dq.append((nx, ny))
    # grass patchiness field
    patch = fractal(random.Random(7))
    px = cell // sub
    img = Image.new("RGB", (W * cell, H * cell))
    dr = ImageDraw.Draw(img)
    for y in range(sh):
        for x in range(sw):
            ch = sg[y][x]
            lx, ly = x // sub, y // sub
            hsh = ((x * 73856093) ^ (y * 19349663)) & 0xFF
            if ch == "W":
                base = WATER_DEPTH[min(3, max(1, depth[ly][lx]))]
                vary = (hsh % 7) - 3
            elif ch == "S":
                wet = any(0 <= lx + dx < W and 0 <= ly + dy < H and grid[ly + dy][lx + dx] == "W"
                          for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)])
                base = (219, 196, 138) if wet else BASE["S"]
                vary = (hsh % 5) - 2
            elif ch == "G":
                base = BASE["G"]
                vary = int((patch[ly][lx] - 0.5) * 22) + (hsh % 5) - 2
            elif ch == "P":
                base = BASE["P"]; vary = (hsh % 7) - 3
            else:
                base = BASE[ch]; vary = (hsh % 9) - 4
            col = tuple(max(0, min(255, c + vary)) for c in base)
            dr.rectangle([x * px, y * px, (x + 1) * px - 1, (y + 1) * px - 1], fill=col)
    # vegetation detail, clipped inside each logical cell
    rng = random.Random(99)
    for y in range(H):
        for x in range(W):
            ch = grid[y][x]
            if ch == "F":
                hcell = (x * 31 + y * 17) % 12
                if hcell == 0:
                    continue  # bare patch inside the woods
                if hcell <= 3:
                    cx, cy = x * cell + 8, y * cell + 8
                    dr.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill=(52, 118, 58))
                    continue
                shades = [(40, 102, 48), (52, 118, 58), (64, 134, 68), (46, 112, 54)]
                for i in range(2 + (hcell % 3)):
                    cx = x * cell + 4 + rng.randint(0, 8)
                    cy = y * cell + 4 + rng.randint(0, 8)
                    r = rng.choice([3, 4, 4, 5, 6])
                    dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=shades[rng.randrange(len(shades))])
            elif ch == "G" and ((x * 13 + y * 29) % 5) == 0:
                for _ in range(2):
                    tx = x * cell + 3 + rng.randint(0, cell - 6)
                    ty = y * cell + 3 + rng.randint(0, cell - 6)
                    dr.line([tx, ty + 2, tx + 1, ty - 2], fill=(84, 148, 84))
    # feature markers
    if feats:
        for c in feats["clearings"]:
            cx, cy = c["x"] * cell + cell // 2, c["y"] * cell + cell // 2
            if c["name"] == "spawn":
                dr.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], outline=(255, 255, 255), width=2)
                dr.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=(255, 255, 255))
            elif c["name"] == "camp":
                dr.line([cx - 5, cy + 4, cx + 5, cy - 4], fill=(110, 72, 40), width=2)
                dr.line([cx - 5, cy - 4, cx + 5, cy + 4], fill=(110, 72, 40), width=2)
                dr.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=(240, 130, 50))
            else:
                for a in range(6):
                    ang = a * 1.047
                    sx, sy = int(cx + 7 * math.cos(ang)), int(cy + 7 * math.sin(ang))
                    dr.ellipse([sx - 2, sy - 2, sx + 2, sy + 2], fill=(150, 150, 150))
    img.save(path)
    bad = 0
    for y in range(sh):
        for x in range(sw):
            for dx, dy in [(1, 0), (0, 1)]:
                nx, ny = x + dx, y + dy
                if nx < sw and ny < sh:
                    a, b = sg[y][x], sg[ny][nx]
                    if (a == "W" and b in "GF") or (b == "W" and a in "GF"):
                        bad += 1
    return bad

TILE_IDS = {"W": 1, "S": 2, "G": 3, "F": 4, "P": 5}
VERSION = "5.0.0"

def gate_failures(sb, feats_ok):
    fails = []
    if sb["water_grass_adjacencies"] != 0: fails.append("water touches land directly")
    if not (0.08 <= sb["sand_share"] <= 0.25): fails.append("sand share out of band")
    if sb["sand_orphan_cells"] > 10: fails.append("orphan sand")
    if not (0.10 <= sb["water_share"] <= 0.35): fails.append("water share out of band")
    if sb["land_share"] < 0.45: fails.append("land share too low")
    if sb["single_cell_regions"] > 25: fails.append("too many single-cell regions")
    if sb["mean_region_size"] < 8: fails.append("regions too small")
    if not all(r < 60 for r in sb["water_roundness_P2_over_A"]): fails.append("water shape too spiky")
    if sb.get("land_regions", 99) != 1: fails.append("land not one region")
    if not all(fs["p2_over_a"] < 90 and fs["core_ratio"] >= 0.15 for fs in sb.get("forest_shape", [])):
        fails.append("forest shape too thin")
    if not (0.15 <= sb.get("water_left_share", 0) <= 0.85): fails.append("water stacked left/right")
    if not (0.15 <= sb.get("water_top_share", 0) <= 0.85): fails.append("water stacked top/bottom")
    if sb.get("quadrant_non_grass_min", 0) < 0.04: fails.append("a quadrant is bare grass")
    if not feats_ok: fails.append("features/path check failed")
    return fails

def generate_one(seed, water_share, forest_moist):
    """One candidate. Returns dict with grid/feats/sb/passed/failures, or None on contradiction."""
    layout, elev, moist = build_layout(seed, water_share, forest_moist)
    grid = solve(layout, moist, seed)
    if grid is None:
        return None
    grid = cleanup(grid)
    out = add_features(grid, seed)
    if out is None:
        sb = scoreboard(grid)
        return {"seed": seed, "grid": grid, "feats": None, "sb": sb,
                "passed": False, "failures": gate_failures(sb, False)}
    grid, feats = out
    # the path carve can slice a 2-3 cell forest fragment off a bigger stand;
    # clear those specks on the final grid (F to G can never break a rule,
    # forest never touches water)
    g2 = [list(r) for r in grid]
    for cells in components(g2, "F"):
        if len(cells) <= 3:
            for (x, y) in cells:
                g2[y][x] = "G"
    grid = ["".join(r) for r in g2]
    feats_ok = check_features(grid, feats)
    sb = scoreboard(grid)
    fails = gate_failures(sb, feats_ok)
    return {"seed": seed, "grid": grid, "feats": feats, "sb": sb,
            "passed": not fails, "failures": fails}

def generate_passer(start_seed, max_attempts, water_share, forest_moist, want=1, log=None):
    """Draw seeds forward until `want` verified passers are found or the cap hits.
    Returns (passers, attempts, last_failures). Never returns a failing map as a passer."""
    passers, attempts, last_failures = [], 0, []
    seed = start_seed
    while attempts < max_attempts and len(passers) < want:
        r = generate_one(seed, water_share, forest_moist)
        attempts += 1
        if r is None:
            last_failures = ["solver contradiction"]
            if log: log(f"seed {seed}: contradiction")
        else:
            last_failures = r["failures"]
            if log: log(f"seed {seed}: {'PASS' if r['passed'] else 'fail (' + (r['failures'][0] if r['failures'] else '?') + ')'} beauty={beauty(r['sb'])}")
            if r["passed"]:
                passers.append(r)
        seed += 1
    passers.sort(key=lambda r: beauty(r["sb"]))
    return passers, attempts, last_failures

def export_map(grid, feats, sb, prefix, params=None):
    import platform
    try:
        import PIL
        pil_v = PIL.__version__
    except Exception:
        pil_v = "unknown"
    meta = {"tool": "wfc5", "version": VERSION,
            "python": platform.python_version(), "pillow": pil_v,
            "params": params or {}, "gates_passed": not gate_failures(sb, feats is not None and check_features(grid, feats)),
            "size": [W, H], "legend": {"W": "water", "S": "sand", "G": "grass", "F": "forest", "P": "path"},
            "origin": "grid[0][0] is the top-left cell; x grows right, y grows down",
            "grid": ["".join(r) for r in grid], "features": feats, "scoreboard": sb}
    with open(prefix + ".json", "w") as f:
        json.dump(meta, f, indent=2)
    # tileset image so the TMX opens usefully in Tiled
    ts = Image.new("RGB", (16 * 5, 16), (0, 0, 0))
    td = ImageDraw.Draw(ts)
    for i, ch in enumerate(["W", "S", "G", "F", "P"]):
        td.rectangle([i * 16, 0, i * 16 + 15, 15], fill=BASE[ch])
    import os
    ts_path = os.path.join(os.path.dirname(os.path.abspath(prefix + ".tmx")), "wfc_tileset.png")
    ts.save(ts_path)
    rows = []
    for y in range(H):
        rows.append(",".join(str(TILE_IDS[grid[y][x]]) for x in range(W)))
    tmx = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           f'<!-- generated by wfc5 {VERSION} params={params} -->\n'
           f'<map version="1.10" tiledversion="1.10.2" orientation="orthogonal" renderorder="right-down" width="{W}" height="{H}" tilewidth="16" tileheight="16">\n'
           ' <tileset firstgid="1" name="terrain" tilewidth="16" tileheight="16" tilecount="5" columns="5">\n'
           '  <image source="wfc_tileset.png" width="80" height="16"/>\n </tileset>\n'
           ' <layer id="1" name="terrain" width="' + str(W) + '" height="' + str(H) + '">\n'
           '  <data encoding="csv">\n' + ",\n".join(rows) + '\n  </data>\n </layer>\n</map>\n')
    with open(prefix + ".tmx", "w") as f:
        f.write(tmx)
    with open(prefix + ".txt", "w") as f:
        f.write("\n".join("".join(r) for r in grid))
    return meta

def load_grid_file(path):
    if path.endswith(".json"):
        d = json.load(open(path))
        rows = d["grid"]
        feats = d.get("features")
    else:
        rows = [ln.strip() for ln in open(path) if ln.strip()]
        feats = None
    return ["".join(r) for r in rows], feats

def make_sheet(cands, path):
    cols = 6
    tw, th, lab = W * 6, H * 6, 16
    rows_n = (len(cands) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (tw + 4) + 4, rows_n * (th + lab + 4) + 4), (24, 24, 24))
    dr = ImageDraw.Draw(sheet)
    import os
    for i, r in enumerate(cands):
        tmp = f"_thumb_{r['seed']}.png"
        render(r["grid"], tmp, cell=6, sub=2, feats=r["feats"])
        x0 = 4 + (i % cols) * (tw + 4); y0 = 4 + (i // cols) * (th + lab + 4)
        sheet.paste(Image.open(tmp), (x0, y0))
        os.remove(tmp)
        label = f"seed {r['seed']} PASS b={beauty(r['sb'])}" if r["passed"] else f"seed {r['seed']} fail: {r['failures'][0] if r['failures'] else 'contradiction'}"
        dr.text((x0 + 2, y0 + th + 3), label[:44], fill=(120, 255, 120) if r["passed"] else (255, 120, 120))
    sheet.save(path)

def die(msg, code=2):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)

if __name__ == "__main__":
    import argparse, os, sys
    ap = argparse.ArgumentParser(description="Guided WFC terrain and level generator (production build). Every map it writes has passed all gates, or it writes nothing and exits nonzero.")
    ap.add_argument("--size", type=int, default=32, help="square size, 16 to 128")
    ap.add_argument("--width", type=int, default=None, help="override width (default: size)")
    ap.add_argument("--height", type=int, default=None, help="override height (default: size)")
    ap.add_argument("--seeds", type=int, default=24, help="shop: passers wanted is 4, attempts capped by --max-attempts")
    ap.add_argument("--seed", type=int, default=None, help="single seed; retries forward until a verified passer is found")
    ap.add_argument("--max-attempts", type=int, default=200, help="seed attempt cap before the tool refuses")
    ap.add_argument("--water", type=float, default=0.20, help="water share, safe range 0.12 to 0.28")
    ap.add_argument("--forest", type=float, default=0.60, help="forest moisture threshold, safe range 0.55 to 0.68 (lower is more forest)")
    ap.add_argument("--out", default="map_v5", help="output prefix; writes PREFIX.png/.json/.tmx/.txt")
    ap.add_argument("--sheet", action="store_true", help="also write a labelled contact sheet of the candidates tried")
    ap.add_argument("--verify", default=None, help="verify an existing .txt or .json grid against all gates, write nothing")
    ap.add_argument("--allow-unguaranteed", action="store_true", help="on total failure, write the best failing map with a .FAILED marker and exit 3")
    ap.add_argument("--debug", action="store_true", help="show tracebacks instead of clean errors")
    args = ap.parse_args()

    if args.verify:
        try:
            grid, feats = load_grid_file(args.verify)
        except Exception as e:
            die(f"cannot read {args.verify}: {e}")
        W = len(grid[0]); H = len(grid)
        try:
            sb = scoreboard(grid)
        except Exception as e:
            die(f"cannot verify {args.verify}: {e}")
        if feats:
            fails = gate_failures(sb, check_features(grid, feats))
            fchecked = True
        else:
            fails = gate_failures(sb, True)  # terrain gates only; file carries no features
            fchecked = False
        print(json.dumps({"file": args.verify, "size": [W, H], "gates_passed": not fails,
                          "features_checked": fchecked, "failures": fails, **sb}, indent=2))
        sys.exit(0 if not fails else 1)

    # validation: clean errors, exit 2, never a traceback for bad input
    W = args.width or args.size
    H = args.height or args.size
    if not (16 <= W <= 128 and 16 <= H <= 128):
        die(f"size must be between 16 and 128 (got {W}x{H})")
    if not (0.12 <= args.water <= 0.28):
        die(f"--water must be in the safe range 0.12 to 0.28 (got {args.water})")
    if not (0.55 <= args.forest <= 0.68):
        die(f"--forest must be in the safe range 0.55 to 0.68 (got {args.forest})")
    if args.seed is not None and args.seed < 0:
        die("--seed must be 0 or more")
    if args.max_attempts < 1:
        die("--max-attempts must be at least 1")
    outdir = os.path.dirname(os.path.abspath(args.out))
    if not os.path.isdir(outdir):
        die(f"output directory does not exist: {outdir}")

    params = {"width": W, "height": H, "water": args.water, "forest": args.forest}
    t0 = time.time()
    try:
        if args.seed is not None:
            passers, attempts, last_fail = generate_passer(args.seed, args.max_attempts, args.water, args.forest, want=1, log=print)
            mode = "single"
        else:
            # shop: try up to --seeds candidates first, keep drawing if none passed yet
            passers, attempts, last_fail = generate_passer(0, max(args.seeds, 1), args.water, args.forest, want=4, log=print)
            if not passers:
                more, att2, last_fail = generate_passer(args.seeds, args.max_attempts - args.seeds, args.water, args.forest, want=1, log=print)
                attempts += att2
                passers = more
            mode = "shop"
    except Exception as e:
        if args.debug:
            raise
        die(f"generation failed: {type(e).__name__}: {e}", code=3)

    if not passers:
        if args.allow_unguaranteed:
            r = generate_one(args.seed or 0, args.water, args.forest)
            if r is not None:
                render(r["grid"], args.out + ".FAILED.png", feats=r["feats"])
                export_map(r["grid"], r["feats"], r["sb"], args.out + ".FAILED", params)
                print(f"wrote UNGUARANTEED failing map to {args.out}.FAILED.* (gates failed: {r['failures']})", file=sys.stderr)
        die(f"no seed passed all gates in {attempts} attempts (last failures: {last_fail}); nothing written", code=3)

    if args.sheet and args.seed is None:
        cands = []
        for s in range(args.seeds):
            r = generate_one(s, args.water, args.forest)
            if r is not None:
                cands.append(r)
        if cands:
            make_sheet(cands, "contact_sheet_v5.png")
            print("wrote contact_sheet_v5.png")
    keeper = passers[0]
    params["seed_requested"] = args.seed
    params["seed_used"] = keeper["seed"]
    params["attempts"] = attempts
    bad = render(keeper["grid"], args.out + ".png", feats=keeper["feats"])
    export_map(keeper["grid"], keeper["feats"], keeper["sb"], args.out, params)
    result = {"version": VERSION, "mode": mode, **params,
              "passers_found": len(passers), "beauty": beauty(keeper["sb"]),
              "gates_passed": True, "failures": [],
              "render_subcell_water_land_adjacencies": bad,
              "seconds": round(time.time() - t0, 1),
              "features": keeper["feats"], **keeper["sb"]}
    with open("result_v5.json", "w") as f:
        json.dump(result, f, indent=2)
    print(json.dumps({"keeper_seed": keeper["seed"], "attempts": attempts, "gates_passed": True,
                      "beauty": beauty(keeper["sb"]), "seconds": result["seconds"],
                      "outputs": [args.out + e for e in (".png", ".json", ".tmx", ".txt")]}, indent=2))
