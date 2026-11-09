# Split memory into topics

Use when your core memory file is growing past a few thousand characters and detail from different domains is piling into one file.

## The prompt (paste this to your Muse)

> My memory file has grown too big and mixes too many domains. Split it into a lean core plus one topical file per domain.
>
> 1. Keep the core file to pointers and hard rules only — who the user is, closed topics, standing preferences, and one line per domain pointing at its file.
> 2. Create one file per domain under `memory/topics/` (kebab-case names). Each file starts with Scope / Do NOT put here / Trigger / Where full detail lives.
> 3. Create a new topical file when ANY of these is true:
>    - New separate domain, client, account, or audience — one file per client, never merge two clients, and never mix separate audiences.
>    - Recurring — expected to be referenced in 3 or more separate chats, or across more than a week.
>    - Volume — its summary would exceed about 15 lines in core, or it carries specs, styles, file paths, or open decisions that must persist.
>    - Separation risk — mixing it into another file could leak it (client A vs client B, personal vs public).
>    - Own workspace — it has its own goal workspace, side chat, account, or approval gate.
> 4. Do NOT create a new file for a one-off question or a single chat (keep it in that chat / daily log), a sub-item of an existing file, or only a date/status update (update the existing file).
> 5. Write an index (`memory/topics/INDEX.md`) listing each file with its trigger — the one sentence that decides when to read it.
> 6. When a project closes: remove its pointer from core, keep the file unless told to scrub it, and never load a closed file for a new task.
> 7. Tell me in one short line per file: file name + trigger.
>
> After the split, verify by measuring the core file's size before and after.

## Why it works

One topical file loads at a time, only when its trigger matches — so a question about one domain never drags in every other domain. In the first pass here, the core file went from about 20,000 bytes to about 10,000 bytes, and each domain file stayed small enough to read whole when needed.
