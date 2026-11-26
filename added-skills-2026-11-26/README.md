# Added skills, 2026-11-26

From a widely shared list of "the best 25 skills you can use with Muse."
We reviewed all 25 against what this toolkit already does. Most duplicated
built in skills or our own tailored ones, so we only took the two real gaps.
Both were tested on a real project before being added here.

## What is in this folder

- `seo-audit/` and `cro/`, plus their shared foundation `product-marketing/`
  Written by Corey Haines, from https://github.com/coreyhaines31/marketingskills
  (MIT License, see `LICENSE-marketingskills`). Copied with the `evals/`
  folders left out, since those need Claude Code only tooling.
  Our local notes are in each skill's `LOCAL-AMENDMENT.md` where present.
- `remotion-local-notes.md`
  Our own notes on using the official Remotion agent skills. The Remotion
  skills themselves are not copied here; get them from
  https://github.com/remotion-dev/skills and follow our notes for the local
  setup that actually works on a small Linux VM.

## Test results (2026-11-26)

- SEO Audit and CRO ran on a real landing page (a small business social
  media prototype). Top finds: no meta description, thin content at about
  300 words, no local SEO signals, an H1 that was only a brand name, and a
  "see a sample" section that showed a terminal command to business owners.
- Remotion rendered a captioned 6 second 1080x1920 test Short locally.
  Captions switched on time, frames were checked at phone size. One catch,
  in the notes file: Remotion's bundled browser download stalls on some
  proxied VMs, so render with a local headless Chrome instead.

## How we keep them

Parked, not always loaded. A one line index entry points at each skill and
it is only read when a task matches, which keeps the standing context cost
at zero. That pattern is worth copying on its own.
