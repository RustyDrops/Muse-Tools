# Handoff summary

Use when a conversation is getting long and the work should continue in a fresh chat without dragging the whole history along.

## The prompt (paste this to your Muse)

> Write a handoff summary for this conversation so a fresh chat can continue the work without re-reading the history.
>
> - Decisions made, with the exact wording of any rule the user set.
> - Open items, with who owes what and what would unblock each one.
> - Things considered and rejected, with the one-line reason for each — judgments, not user closures, recorded so they aren't re-audited or re-proposed next time.
> - Verified facts (numbers, dates, file paths) — only ones checked against a source.
> - What was explicitly declined or closed, so it isn't re-raised.
> - File paths of anything built, and what still needs doing to each.
>
> Keep it short: a summary, not a transcript. Never paste full files, logs, or transcripts into it. Save it to `handoffs/<slug>.md` and tell me in one line where it is. In the new chat, load only that summary — not the old conversation.

## Why it works

A fresh chat with a good handoff is cheaper than a long chat carrying stale context, and the summary is the one place the decisions live — so a correction made once doesn't have to be made again.
