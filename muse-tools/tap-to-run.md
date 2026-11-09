# Tap-to-Run Launcher — click-to-run pattern

A tap never runs a tool by itself. Each row is a `send_message` list row:
tapping it sends that exact text as the user's message, Muse then runs the
tool, checks the result, and reports back. A tap can never post, send,
delete, approve, or bypass the QA gate.

LOCK BEHAVIOUR (verified 2026-10-27): a list widget locks after one tap
(`locked: true`, `selectedText` = the tapped row) and Muse cannot unlock or
reset it — widget state is read-only for Muse. Re-presenting the same
widget_id does NOT clear it. Fix: create a NEW list widget (new widget_id)
for the launcher, and Muse must re-issue a fresh launcher after every tool
run, or the user is stuck on the last choice.

Rows (exact send_message text):
- "Run the Context Meter" → `python3 ~/workspace/muse-tools/context-meter.py`
- "Show job health" → Job Health Board procedure in `job-health.md`
- "Make a handoff summary" → `handoff.py new <slug> --title "<title>"`, then fill its sections
- "Show delegate costs" → `python3 ~/workspace/muse-tools/cost-ledger.py`
- "Show the Tap-to-Run Launcher" → re-create this list in the current chat

Labels use emoji + text, never an emoji alone as a button icon.
Outputs are short: result + exceptions + what needs the user's decision.
Files are referenced by path, never re-sent.
