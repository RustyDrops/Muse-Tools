# Daily memory cleanup

Run once a day (a scheduled job works). It keeps the core memory file under its cap without losing anything that matters.

## The prompt (paste this to your Muse, or use it as a daily scheduled job)

> Check the size of my core memory file.
>
> - If it is under 12,000 characters, do nothing and say nothing.
> - If it is over 12,000 characters, condense it in place:
>   - Move detail into the matching topical file (create one first if the domain has no file yet, using the split prompt).
>   - Keep in core only pointers, hard rules, closed topics, and standing preferences — nothing that belongs in a topical file.
>   - Never delete a closed item, a hard stop, or a standing rule. Condense wording, don't drop decisions.
>   - Never move private detail into a shared or group memory file.
> - After condensing, re-check the size and confirm it is under the cap, and that every pointer still points at a file that exists.
>
> Report only what changed: size before and after, and which files gained detail. Stay silent when nothing needed doing.

## Why it works

Memory grows a little every day; without a cap it quietly eats the context window. A nightly check that stays silent when there's nothing to do costs nothing on quiet days and stops the slow bleed.
