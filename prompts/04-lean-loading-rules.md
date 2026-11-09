# Lean loading rules

The everyday habits that keep context small. Give these to your Muse as standing instructions, not a one-off prompt.

## The rules

1. Heavy work in a fresh side chat; the main chat is for short questions.
2. One agent by default; at most two parallel subagents for independent chunks, never a coordinator chain. A subagent inherits the parent's full context, so spawn from the smallest parent chat, with a narrow brief, and a short summary back only.
3. Prefer a cheap delegate model for non-personal drafts and checks; keep the main model for small edits, personal material, time-critical work, and final quality checks.
4. Batch instructions, run to completion, review once.
5. Cap tool output: targeted reads only, work from files, report results only — never paste full files, transcripts, or logs into chat.
6. Scripts over chat turns; deterministic checks, not re-reads. Handoff summary over full history.
7. Short outputs by default: result + exceptions + what needs the user's decision. Never re-send the same file, deck, audio, or image — reference it by path.
8. Memory on demand: one topical file plus one goal file when they match, never all of them. Widgets are display only — the file is the source of truth.
9. Verify every factual claim before presenting it, especially numbers, dates, prices, addresses, and availability. If it can't be verified, say so plainly instead of filling the gap.
10. When the user corrects a fact, fix it everywhere it lives the same turn — stale copies are how the same mistake ships twice.
