# Step 1 — Generalized deterministic QA suite build brief

Source plan: `~/workspace/efficiency-tools-2026-11-07/PLAN.md`, Step 1. Build only this step. No other tool, no installs, no API calls, no generative imagery.

## Goal
Generalize the proven layout-checker pattern (`check_layout` + `auto_fix`) into one QA CLI for code, image, and audio, with a local auto-fix first and a delegate fix round only if unfixable (the QA suite itself never calls a delegate).

## Files to create (all under `~/workspace/efficiency-tools-2026-11-07/qa-suite/`)
- `qa_suite.py` — CLI: `qa_suite.py check <code|image|audio> <path> [--fix]`. Exit 0 PASS / 1 FAIL / 2 checker-error (mirrors `auto_fix.py` exit codes). Prints one JSON verdict with exact measurements per failure. With `--fix`, runs the local auto-fix first and only reports `unfixable` (with measurements attached) when a delegate fix round is justified — it never calls one itself.
- `checks_code.py` — Python test runner + linter wrapper (runs the target's own `pytest`/`unittest` and the repo-configured linter if present; FAIL lists test names and first failure lines by path, never pastes whole logs into chat — full log to a file on disk). Use the tools-venv python for pytest (`~/workspace/tools-venv/bin/python -m pytest`); system python3 has no pytest.
- `checks_image.py` — image checker: dimensions/format, text overflow and type floor by reusing `check_layout` for Pillow scripts and `check_block` semantics for rendered PNGs, contrast via the `brands.js`/`design-quality.js` thresholds (4.5:1 body, 3:1 large text), blank-image floor (stddev, as in `pillow-templates/qa.py`).
- `checks_audio.py` — audio length/format checker: `ffprobe` format/duration/sample-rate, loudness via the existing two-pass loudnorm measurement pattern (target -14 LUFS Shorts / -16 LUFS sermon, tolerance 1 LUFS as in `shorts.py`).
- `test_qa_suite.py` — fixture tests: known-good and known-bad code/image/audio fixtures, including the three `auto_fix` proof cases from the handoff (turn-1 FAIL must reach PASS; below-floor type must be restored, not passed; already-passing input is a no-op).

## Reuse untouched (import by path, never copy)
`layout-tools/qa_tools.py` (`check_layout`), `layout-tools/auto_fix.py` (`auto_fix_file`), `delegate_qa_orchestrator.py` (`extract_layout`/`check_code` — extractor errors stay exit 2, never a delegate round), `~/workspace/github-upload/muse-social-graphics-suite-remote-73ca3e4e/pillow-templates/qa.py`, `~/workspace/github-upload/muse-social-graphics-suite-remote-73ca3e4e/socialforge/qa.py` (gate semantics: runs last, blocks on FAIL), `~/workspace/github-upload/muse-social-graphics-suite-remote-73ca3e4e/socialforge/creators/audio.py` (loudnorm measurement). Known extractor gotchas: `body_top = y + 66` variable form and the `pill_width, pill_height = 720, 58` tuple — add one fixture per new script shape before trusting a PASS.

## Chunks/models
Write all checkers + tests (deterministic, measurement-heavy file work). A cheap delegate model drafts fixture copy/text only — do NOT call one in this build; leave fixture copy as short placeholders if needed, a later delegate chunk will draft them. A stronger delegate model only if a checker chunk fails twice at low — not expected, and not in this build.

## Check (must PASS before returning)
- `~/workspace/tools-venv/bin/python -m pytest qa-suite/test_qa_suite.py -q` -> PASS
- Live proof: `python3 qa-suite/qa_suite.py check image <known-bad-layout.py> --fix` -> JSON `"pass": true` after local fix with `delegate_cost_usd: 0.0`; the below-floor fixture -> `"unfixable"` only after type restoration fails, with exact px measurements attached.

## Out of scope
Calling a delegate model from inside the QA suite; subjective/aesthetic judgment (stays with the existing visual-review path); any new linter dependency (use what the target repo already configures).

## Rules
- A checker must NEVER pass by shrinking type — floor asserted in `check_layout` and re-asserted in tests (title >= 34, body >= 28).
- Never paste large files into chat; outputs live on disk, referenced by path.
- Known environment note: inside a sandboxed shell, calls can fail with `bwrap: Can't mount proc` — if you cannot execute checks inside the sandbox, say so in your return and leave the checks for verification outside; do not fake a PASS.
- Stop if a check fails twice on the same error — record the gap and return, do not loop.
- Use bare `pytest` (tools-venv), never `python3 -m pytest` in any command the delegate loop would run (the loop refuses `-m`); running it in your own shell is fine.
