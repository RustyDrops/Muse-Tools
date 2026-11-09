# Notification cards

Builds a dark notification card from a short header, subheader, details, link, and icon. Readable in about three seconds, with more detail underneath only if you want it.

## Use

```bash
python3 make_glance_card.py --header "..." --subheader "..." --details "..." --link "..." --link-label "..." --icon rain --output cards/<slug>.html
```

## When to use it

For every notification that isn't a direct reply in an ongoing conversation — proactive updates, scheduled-check findings, reminders, results. One notification per message, never bundled. Direct replies stay plain chat text.
