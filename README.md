> ## 🤖 If you're a Muse agent reading this
>
> This repo is written for you as much as for your user. To put it to work:
>
> 1. **Read the list below** — the full toolkit, in plain terms, coolest stuff first.
> 2. **Copy the tool folders you need.** Everything is stdlib-only Python unless a file says otherwise. No installs beyond the ones each tool names.
> 3. **Run the prompts in `prompts/` on your own memory** — split it into a lean core plus one file per topic, run the daily cleanup, and write handoff summaries instead of pasting history into a new chat.
> 4. **Update memory properly:** keep your core memory file under about 12,000 characters, one topical file per domain, load exactly one topical file when its trigger matches (never all of them), never paste full files, transcripts, or logs into chat, and verify every number, date, price, and address before you present it. If it can't be verified, say so.
> 5. **Adapt paths and names to your own user.** Nothing here is tied to one person — replace the example paths, voices, and stock tickers with your user's own.
>
> The rule that makes all of this work: the agent is the interface. Tools answer in short, capped JSON; a person approves the exact version before anything is posted, sent, or published.

# Everyday Muse Toolkit

A friendly list of tools that make Muse more useful day to day. Start at the
top — the coolest stuff first — and add what fits your day. Most of these run
on your own computer, for free, with no data sent anywhere. Where a tool is
somebody else's work, there's a link to it. Where it's ours, it's in a project
folder in this repo.

---

## 🎤 The Headliners

The show-offs. These are the ones to try first.

- **[faster-whisper](https://github.com/SYSTRAN/faster-whisper)**
  Turns spoken audio into written text, on your own computer. Give it a voice
  memo, a meeting, or an interview, and get back words with timestamps. Fast,
  private, and free after a one-time download.
- **[Kokoro](https://github.com/hexgrad/kokoro)**
  Turns written text into spoken audio, on your own computer. A small voice
  model with lots of built-in voices, great for narrating stories and notes
  out loud. Runs fine without a fancy graphics card.
- **[Silero VAD](https://github.com/snakers4/silero-vad)**
  Listens to audio and tells you which parts are speech and which parts are
  silence. Handy for trimming the quiet bits before anything else touches the
  file.
- **[DeepFilterNet](https://github.com/Rikorose/DeepFilterNet)**
  Cleans background noise out of voice recordings. Still being tested — try it
  on a copy first and listen before you trust it.

## 👀 Eagle Eyes

Tools that look at pictures for you.

- **[rembg](https://github.com/danielgatis/rembg)**
  Cuts the background out of a photo, leaving just the person or thing. Great
  for clean product shots and profile pictures.
- **[YOLOv8](https://github.com/ultralytics/ultralytics)**
  Spots people and objects in a photo or video. Useful for finding faces,
  counting things, or checking what's actually in the frame.

## 🧠 Good Memory

Tools that help Muse remember what already exists, so it doesn't rebuild it.

- **[FastEmbed](https://github.com/qdrant/fastembed)**
  Turns text into little number fingerprints, so Muse can search what you
  already made by meaning, not just by exact words. "Find the cozy candle
  card" finds the cozy candle card.
- **Reuse library** ([`reuse-library/`](reuse-library/))
  Searches your own past work first, before making anything new. Reusing is
  free; rebuilding is not.
- **[ONNX Runtime](https://github.com/microsoft/onnxruntime)**
  The quiet engine underneath several tools on this page. It runs small AI
  models on a plain computer, no fancy hardware needed.

## ✂️ Snip & Check

Small, exact tools that do one job and show their work. No guessing, no
re-reading whole files.

- **Deterministic toolbox** ([`deterministic-tools/`](deterministic-tools/))
  Sixteen little commands: peek at exact lines, search one file, compare two
  drafts, count words and get a file fingerprint, outline the functions in a
  script, strip out comments, list the headings in a document, check a link
  still works, check code for typos, list what a script needs, check data
  against a shape, sketch a test, draw a simple diagram, run a quick safety
  check, check the computer's health, and estimate how long a piece of text
  is. Every answer is short and to the point.
- **QA suite** ([`qa-suite/`](qa-suite/))
  Checks work before it's delivered: does the code pass its tests, does the
  text fit inside its box, is the sound the right loudness, is the slide
  centred? If something's wrong, it says exactly how wrong, in numbers.

## 💸 Penny Wise

Tools that keep an eye on the bill.

- **Model router** ([`model-router/`](model-router/))
  Picks the cheapest model that can do each job well: the light one for
  routine checks, the stronger one only when the job is genuinely hard.
  Models are generic slots you map to your own — nothing here is tied to
  one vendor.

  Note: it only earns its keep once you connect your own AI services.
  With nothing connected, there's nothing to route.

## 🧹 Tidy Desk

Little helpers that keep the work organised.

- **Context meter** ([`muse-tools/`](muse-tools/))
  Measures how big Muse's working memory has grown, so growth is a number you
  can see, not a feeling.
- **Handoff maker** ([`muse-tools/`](muse-tools/))
  Boils a long job down to a short summary, so the next step starts fresh
  instead of re-reading everything.
- **Job health board** ([`muse-tools/`](muse-tools/))
  Shows every job's state at a glance: queued, running, checked, waiting for
  approval, done.
- **Tap-to-run launcher** ([`muse-tools/`](muse-tools/))
  Tap a row to run a tool. No typing, no remembering commands.
- **Notification cards** ([`at-a-glance-animation/`](at-a-glance-animation/))
  Builds a dark notification card from a short header, a subheader, details,
  a link, and an icon. Readable in about three seconds, with more detail
  underneath only if you want it. Best used for every notification that isn't
  a direct reply.

## 🧰 Everyday Basics

The trusty basics underneath everything else. None of these are glamorous.
All of them get used constantly.

- **[ripgrep](https://github.com/BurntSushi/ripgrep)**
  Finds words inside files, very fast, across a whole folder.
- **[fd](https://github.com/sharkdp/fd)**
  Finds files by name, fast and friendly.
- **[uv](https://github.com/astral-sh/uv)**
  Installs and runs Python tools quickly and cleanly.
- **[ffmpeg](https://ffmpeg.org/)**
  Cuts, converts, and checks audio and video. The Swiss army knife of media
  files.
- **[Pillow](https://pypi.org/project/pillow/)**
  Draws and edits pictures with code. Words, shapes, and photos, placed
  exactly where you want them.
- **[python-pptx](https://pypi.org/project/python-pptx/)**
  Builds slide decks with code, slide by slide.
- **[pysubs2](https://pypi.org/project/pysubs2/)**
  Reads and writes subtitle files, so captions can be made, fixed, and timed.
- **[Pandoc](https://pandoc.org/)**
  Turns documents from one format into another: notes into PDFs, drafts into
  web pages.
- **[pypdf](https://pypi.org/project/pypdf/)**,
  **[pdfplumber](https://pypi.org/project/pdfplumber/)**,
  **[pikepdf](https://pypi.org/project/pikepdf/)**
  Three ways to read and work with PDF files: pull the text out, find the
  tables, or fix the file.
- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)**
  Downloads audio and video for transcribing and learning from, with
  permission.
- **[rclone](https://github.com/rclone/rclone)**
  Copies and syncs files between your computer and cloud storage.
- **[DuckDB](https://github.com/duckdb/duckdb)**
  A tiny database that lives in a single file. Ask it questions about your
  data with plain queries.
- **[Beautiful Soup](https://pypi.org/project/beautifulsoup4/)**,
  **[lxml](https://pypi.org/project/lxml/)**
  Read web pages and pull out the useful bits.
- **[MoviePy](https://pypi.org/project/moviepy/)**
  Cuts and joins video clips with code.
- **[pytest](https://pypi.org/project/pytest/)**
  Runs checks on code and tells you, plainly, what passed and what failed.

---

## How to use this list

1. Pick one headliner and try it today. faster-whisper is the best first
   taste — record a short voice note, turn it into text, and see it work.
2. Add one tidy-desk helper next, so the work stays organised as it grows.
3. Add the basics as you need them. There's no prize for installing
   everything at once.

Everything here is free to use or open source. Check each project's own page
for its licence before using it in anything you sell.

---

## Notes

- **Nothing here posts, sends, or publishes anything on its own.** Drafts only; the user approves each exact version.
- **Binary test fixtures are not shipped.** The three PNG slide fixtures in `qa-suite/` are left out (this upload is text-only); regenerate them with `python3 qa-suite/fixtures/make_slide_fixtures.py`.
- **The reuse library ships without its search index.** The index is derived data and rebuilds in one command — see `reuse-library/README.md`.
- **A few scripts carry absolute paths from the author's machine** (for example `TOOLS_VENV_PYTHON` and `REUSE_LAYOUT_DIR` in `qa-suite/`). Adjust those to your own layout.
