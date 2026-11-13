# Deterministic toolbox

Stdlib-only local toolbox. Every command prints ONE short JSON object.
Never pastes a whole file into chat. $0, no LLM calls, no installs.
Only network: `check-url` (HTTP HEAD).

## Commands (26)

| Command | Args |
|---|---|
| `peek` | `<path> <start> <end>` — lines [start,end], 1-based; cap 100 lines, 300 chars/line |
| `grep` | `<path> <pattern> [--ignore-case] [--regex]` — cap 50 matches; single file only (`--dir` rejected) |
| `diff` | `<old> <new>` — unified diff; cap 200 lines; exit 1 when different |
| `stats` | `<path>` — lines, bytes, SHA-256, est. tokens (chars/4); no content |
| `outline` | `<pyfile>` — AST classes/functions, signatures, docstring first lines; cap 200 |
| `strip` | `<pyfile> [--out PATH]` — drop comments/docstrings; dry-run counts unless `--out`; never prints code |
| `toc` | `<mdfile>` — headings with level/text/offset; cap 200 |
| `check-url` | `<url>` — HTTP HEAD, 3 s timeout, max 3 redirects, no auth/body |
| `syntax` | `<pyfile>` — thin `ast.parse` check; `line`/`col`/`message` on failure |
| `imports` | `<pyfile>` — AST imports via `find_spec` (no execution); found/missing |
| `validate` | `<jsonfile> <schemafile>` — stdlib schema subset; first 10 errors with paths |
| `scaffold` | `<pyfile> [--out PATH] [--force]` — unittest skeleton; dry-run without `--out`; never overwrites without `--force` |
| `diagram` | `<pyfile> [--out PATH]` — Mermaid classDiagram; dry-run without `--out` |
| `canary` | `<pyfile> [--timeout 10]` — run workspace-only `.py` with timeout; first 6 lines only |
| `health` | no args — mem/loadavg/disk/cgroup; best-effort, always exit 0 |
| `estimate-cost` | `<path> [--output-tokens N] [--rates PATH]` — `cost_usd: null` unless `--rates` given |
| `stamp` | `<out.json> <path> [path...] [--force]` — record per-file SHA-256/size/mtime + git repo/HEAD a brief was written against |
| `drift` | `<stamp.json>` — re-check a stamp; exit 1 + changed paths/reasons on drift, 0 when clean |
| `branch-scope` | `<repo> [--base REF]` — files changed since merge-base with base + direct importers/callers of each (branch-audit scope) |
| `rejected` | `add "<item>" "<reason>" / list / check "<text>" [--project SLUG] [--store PATH]` — persistent considered-and-rejected log (default store `~/workspace/handoffs/rejected.jsonl`); `check` exit 0 when a prior rejection matches |
| `snapshot` | `<target> <out.json> [--force]` — Hallmark pack: inventory before a redesign — links, ids, headings, images, fields, handlers, test hooks + per-file SHA-256 |
| `kept` | `<before.json> <target> [--dropped ITEM ...]` — Hallmark pack: FAIL on anything the original had that the new version lost (links/fields/handlers/ids/hooks), WARN on headings/images, unless recorded as dropped |
| `words` | `<target> [--surface web\|tool\|card\|social\|glance] [--budget N]` — Hallmark pack: word-budget lint per surface (web 80/section, 450 total; card 30; glance 20; social 35/60; tool 120/900) |
| `gatecheck` | `<target> [--surface S] [--stage hero] [--stamp PATH]` — Hallmark pack: tiered gates — Floor never waives (a Floor waiver is rejected), Reflex waivable on the record with guard + specific reason (24+ chars) read from the file/stamp, Finish answered and never blocks. Gates are scoped by surface: web-only bans (tracked caps, purple-blue gradient) are Reflex, not Floor, on social/card |
| `deal` | `<themes-dir> [--log PATH] [--prompt TEXT]` — Hallmark pack: deal 3 themes clearing the last 3 in the rotation log. A theme is a material (one `.md` file, ≤8 KB flagged), never a plan; a build reads exactly one |
| `rotation` | `add\|check\|list --log PATH [--theme T --shape S --hero H --nav N --footer F --signature X] [--waived GATE]` — Hallmark pack: mirror test — a candidate sharing 4+ axes with a recent build FAILs; same gate waived in 3 straight entries is flagged as a house style |
| `brief` | `<out-stamp> --surface S --job J --shape S --theme T --signature X --real R --pictures P --absent A [--critique "P5 H4 E5 S3 R5 V4"] [--theme-file PATH] [--waive TEXT]` — Hallmark pack: Picks block + decision stamp. Material inventory is mandatory — `absent` must be declared (write `none`); facts are never inferred. Stamp records the hero-first stage plan (hero only → gatecheck --stage hero → fresh-context review → the rest) and the pre-emit critique; a score under 3 or a theme file over 8 KB exits 1 |

Validator subset: `type required properties items enum minimum maximum
minLength maxLength pattern`.

## Exit codes

`0` pass/found · `1` fail/not-found (grep miss, syntax fail, validate fail,
diff differs, missing imports) · `2` tool error (missing file, bad args,
out-of-range, canary refusal/timeout, check-url network failure).

## Examples

```sh
python toolbox.py peek fixtures/sample.md 1 3
python toolbox.py grep fixtures/sample.md "Section" --ignore-case
python toolbox.py stats fixtures/sample.md
python toolbox.py outline fixtures/good.py
python toolbox.py strip fixtures/good.py --out /tmp/stripped.py
python toolbox.py syntax fixtures/bad.py
python toolbox.py validate fixtures/sample.json fixtures/schema.json
python toolbox.py estimate-cost fixtures/sample.md --output-tokens 500
python toolbox.py check-url https://example.com
```

## Caps (hard, asserted in tests)

100 peek lines · 50 grep matches · 200 diff lines · 200 outline symbols ·
200 toc headings · 300 chars per line · 10 validate errors · 6 canary lines.

## Notes

- `syntax` is a thin `ast` wrapper; it does not run pytest (unlike
  `qa-suite/checks_code.py`, which is reused by import path only, never copied).
- `estimate-cost` never invents rates: without `--rates`, `cost_usd` is `null`.
- `canary` refuses paths outside `~/workspace` (exit 2) and runs `.py` only.
- Hallmark pack (`snapshot kept words gatecheck deal rotation brief`, in `hallmark_tools.py`): the mechanics of [Nutlope/hallmark](https://github.com/Nutlope/hallmark) (MIT) re-implemented as deterministic code — tiered gates, before/kept preservation, word budgets, theme dealing + rotation, and the brief/decision stamp. Scoped by surface on purpose: Hallmark's web bans are not applied as Floor to social graphics, where a badge pill / tracked label is a legitimate prefab. Examples: `python toolbox.py snapshot page.html before.json` · `python toolbox.py kept before.json page-v2.html` · `python toolbox.py gatecheck card.html --surface social` · `python toolbox.py words page.html --surface web`.
