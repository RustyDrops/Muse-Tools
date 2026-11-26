# Remotion agent skills: local notes

Our own notes, written 2026-11-26 after a live test. The skills themselves
live at https://github.com/remotion-dev/skills (skills used: remotion-create,
remotion-markup, remotion-render, remotion-captions). Install them from
there; this file is the part the upstream docs cannot tell you about our
kind of machine.

## What Remotion is, in one paragraph

Not a hosted service. It is npm packages inside your project. Rendering runs
on your own machine: a headless Chromium draws each frame and the video is
encoded locally. No account, no server. Optional cloud rendering exists but
we do not use it.

## The one catch that cost us an hour, so it costs you nothing

On a proxied Linux VM, Remotion's bundled browser download can stall
(the download host sends no data and times out). The upstream render skill
says to use the bundled browser and not set a browser path. On this kind of
VM that fails. What works:

```
npx remotion render <CompositionId> out/video.mp4 \
  --browser-executable=$HOME/.cache/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-linux64/chrome-headless-shell \
  --license-key=free-license
```

Use the Playwright headless shell already on the machine. Telemetry timeout
messages after a successful render are harmless.

## Rules we render by

- Captions are JSON in the official Caption type, transcribed locally
  (faster-whisper). Audio does not leave the machine for transcription.
- Check stills at phone size, and watch the full render once, before
  calling any Short done.
- Nothing posts without the owner's approval of the exact version.
- Remotion is free for teams of up to 3. Recheck the license before using
  it for client delivery at scale.
- Shorts render fine on a CPU only VM. Long renders belong on a GPU box.

## Test evidence

6 second test Short, 1080x1920, 30fps, H.264, about 550 KB. Three captions
at 0 to 2s, 2 to 4s, and 4 to 6s, an animated waveform, and a progress bar.
Frames at 0.5s, 2.5s, and 5s each showed the right caption and an advancing
progress bar.
