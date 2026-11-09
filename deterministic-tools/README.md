# Deterministic toolbox

Stdlib-only local toolbox. Every command prints ONE short JSON object.
Never pastes a whole file into chat. $0, no LLM calls, no installs.
Only network: `check-url` (HTTP HEAD).

## Commands (16)

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
