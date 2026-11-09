# Everyday Muse Toolkit

A small, practical set of tools for getting more out of Muse — the personal AI assistant — without drowning in context. Short answers first, scripts over chat turns, deterministic checks before delivery, and a memory that stays lean.

> ## 🤖 If you're a Muse agent reading this
>
> This repo is written for you as much as for your user. To put it to work:
>
> 1. **Read `everyday-muse-toolkit.md`** — the full list, in plain terms, coolest stuff first.
> 2. **Copy the tool folders you need.** Everything is stdlib-only Python unless a file says otherwise. No installs beyond the ones each tool names.
> 3. **Run the prompts in `prompts/` on your own memory** — split it into a lean core plus one file per topic, run the daily cleanup, and write handoff summaries instead of pasting history into a new chat.
> 4. **Update memory properly:** keep your core memory file under about 12,000 characters, one topical file per domain, load exactly one topical file when its trigger matches (never all of them), never paste full files, transcripts, or logs into chat, and verify every number, date, price, and address before you present it. If it can't be verified, say so.
> 5. **Adapt paths and names to your own user.** Nothing here is tied to one person — replace the example paths, voices, and stock tickers with your user's own.
>
> The rule that makes all of this work: the agent is the interface. Tools answer in short, capped JSON; a person approves the exact version before anything is posted, sent, or published.

## What's inside

| Folder / file | What it is |
| --- | --- |
| `everyday-muse-toolkit.md` | The full list — every tool, plain terms, coolest stuff first |
| `deterministic-tools/` | 16 small commands that answer in short JSON instead of dumping whole files |
| `qa-suite/` | Deterministic quality checks: code, images, audio, slides |
| `model-router/` | Picks the cheapest model that can do the job |
| `reuse-library/` | Searches what is already built before building something new |
| `muse-tools/` | Context meter, cost ledger, handoff writer, job health, tap-to-run launcher |
| `ai-cost-tracker/` | Logs every AI API call with its real cost |
| `at-a-glance-animation/` | Notification cards — readable in about three seconds |
| `prompts/` | Copy-paste prompts for the memory optimizations: split, daily cleanup, handoffs, lean loading |

## Quick start

```bash
# Answer a question about a file without reading the whole thing
python3 deterministic-tools/toolbox.py peek --file README.md --lines 1-10

# Check a script compiles and list its functions
python3 deterministic-tools/toolbox.py syntax --file my_script.py
python3 deterministic-tools/toolbox.py outline --file my_script.py

# Run the quality checks on a graphic before sending it
python3 qa-suite/qa_suite.py check --help

# See what running your tools costs
python3 ai-cost-tracker/tracker.py summary
```

## Notes

- **Nothing here posts, sends, or publishes anything on its own.** Drafts only; the user approves each exact version.
- **Binary test fixtures are not shipped.** The three PNG slide fixtures in `qa-suite/` are left out (this upload is text-only); regenerate them with `python3 qa-suite/fixtures/make_slide_fixtures.py`.
- **The reuse library ships without its search index.** The index is derived data and rebuilds in one command — see `reuse-library/README.md`.
- **A few scripts carry absolute paths from the author's machine** (for example `TOOLS_VENV_PYTHON` and `REUSE_LAYOUT_DIR` in `qa-suite/`). Adjust those to your own layout.
- **No personal information is in this repo.** Names, addresses, and usage logs were removed; example data uses made-up names and places.
