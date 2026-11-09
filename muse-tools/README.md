# Muse Tools — built Muse-led, 2026-10-27

Four small tools, one focused job each. None posts, sends, deletes,
approves, or bypasses a QA gate on its own.

1. **Context Meter** — `context-meter.py`
   Measured sizes (bytes, approx. tokens, lines) for MEMORY.md, topical,
   people, and group files. No file contents printed.
   Run: `python3 ~/workspace/muse-tools/context-meter.py`

2. **Job Health Board** — `job-health.md`
   Muse procedure using live `cron.list` / `cron.status` / `cron.runs`,
   user jobs only, system jobs counted as a group. Read-only: never
   delete and recreate a working job to repair it.

3. **Handoff Summary Maker** — `handoff.py`
   Creates a short summary file in `~/workspace/handoffs/` to seed a fresh
   side chat. No transcripts, logs, or pasted content.
   Run: `python3 ~/workspace/muse-tools/handoff.py new <slug> --title "<title>"`

4. **Tap-to-Run Launcher** — `tap-to-run.md` + list widget in chat
   Tap a row → it sends that request as the user's message → Muse runs the
   tool and reports back. See `tap-to-run.md` for exact row texts.

Invoke any of them in chat by name, e.g. "Run the Context Meter" or
"Show delegate costs". Church and personal reports stay in separate chats.
README: turn-time.py — manual turn-time log, see script header
