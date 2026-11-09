# Step 2 — Reuse library build brief

Source plan: `~/workspace/efficiency-tools-2026-11-07/PLAN.md`, Step 2. Build only this step. No other tool, no installs, no API calls, no generative imagery.

## Goal
Local FastEmbed search over existing code/graphics/templates so work is reused ($0) instead of regenerated. Search returns paths + scores + one-line labels only; file contents stay on disk.

## Files to create (all under `~/workspace/efficiency-tools-2026-11-07/reuse-library/`)
- `reuse_library.py` — CLI: `index --sources reuse_sources.json`, `search --query "..." [--kind code|graphic|icon|template]`. Indexing extracts text (docstrings/headings/slot names/registry metadata — never whole-file dumps), embeds with FastEmbed (`BAAI/bge-small-en-v1.5`, 384 dims) from `~/workspace/tools-venv`, stores `{path, kind, title, vector}` in a local JSONL/npz index on disk. Search returns the top matches as `path + score + one-line label` only.
- `reuse_sources.json` — read-only source list: existing scripts (`layout-tools/*.py`), card layouts (`pillow-templates/registry.json`, `content.json`), icons (`engine/shared/icons.js`), templates (Pillow registry + Node template registry), `muse-designer/` prefabs. Paths are under `~/workspace/github-upload/muse-social-graphics-suite-remote-73ca3e4e/` — verify each path exists before indexing; record any missing path as a gap, do not invent one.
- `test_reuse_library.py` — fixture index over a tiny temp corpus; asserts a known query returns the known path first.
- Index output (generated, on disk, not chatted): `reuse-library/index/` (vectors + manifest with source mtimes for incremental re-index).

## Reuse untouched
FastEmbed in `~/workspace/tools-venv` (no install; run with that venv's python), all indexed source files (read-only), `~/workspace/muse-tools/context-meter.py` pattern (measure, never print contents).

## Chunks/models
Write indexer/search/tests (file/embedding plumbing). A cheap delegate model drafts the one-line label extraction prompts/heuristic wording only — do NOT call one in this build; leave label wording as short placeholders if needed, a later delegate chunk will draft them. Extraction itself is deterministic (AST/regex/registry fields, reusing the orchestrator's extractor approach). No generative anything.

## Check (must PASS before returning)
- `~/workspace/tools-venv/bin/python -m pytest reuse-library/test_reuse_library.py -q` -> PASS
- `~/workspace/tools-venv/bin/python reuse-library/reuse_library.py search --query "polaroid family photo card" --kind template` -> top hit is the `side-polaroid-family` template path with a score, and no file contents in stdout.

## Out of scope
Indexing church/personal data or anything outside the listed source roots; semantic search over images by pixels (text/metadata only in v1); any delegate call before a search has run (workflow rule, enforced by the router reason string, not by code lockout).

## Rules
- Embed in small batches, one model at a time (VM is 4 CPU / 7.7 GB RAM); index incrementally by mtime, never re-embed unchanged files.
- One parser per kind, one fixture per kind; stale index pointing at moved files = reported gap, search continues.
- Never paste large files into chat; outputs live on disk, referenced by path.
- Known environment note: inside a sandboxed shell, calls can fail with `bwrap: Can't mount proc` — if you cannot execute checks inside the sandbox, say so in your return and leave the checks for verification outside; do not fake a PASS.
- Stop if a check fails twice on the same error — record the gap and return, do not loop.
- Use bare `pytest` (tools-venv), never `python3 -m pytest` in any command the delegate loop would run; running it in your own shell is fine.
