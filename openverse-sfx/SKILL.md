# Openverse Sound Effects - Free, Licensed, Drop-In

Add real sound effects to videos, games and apps for $0, with the license
checked before anything ships. Source: Openverse (api.openverse.org),
which indexes Freesound, Wikimedia and other free libraries.

No generative audio. No account. No API key.

## The workflow (follow it in order)

1. **List the sound jobs first.** Never browse aimlessly. Write the exact
   moments that need sound before searching:
   - Video / Short: hook pop, typing ticks, transition whoosh, payoff chime,
     error buzz, notification ping.
   - Game: jump, land, coin or pickup, hit, hurt, death, power-up, checkpoint,
     win, lose, UI click, door, splash, step.
   - App / UI: click, toggle, success, error, send, delete.
2. **Search per job** with `openverse_sfx.py search "<words>"` in this
   folder, or the Openverse API directly. Short, concrete words win:
   "bubble pop", "keyboard clicks", "coin pickup", "chime notification".
3. **License rule: CC0 first.** CC0 1.0 means public domain, no attribution
   legally required, commercial use fine. Only fall back to CC BY when CC0
   has nothing usable, and then the credit line is mandatory, in the video
   description, the game credits screen, or a CREDITS file in the repo.
   Never use a sound whose license you have not read on its Openverse
   detail record. The search snippet is not proof, the detail record is.
4. **Download** with `openverse_sfx.py get "<words>" --out <folder>`.
   It writes CREDITS.md automatically. Keep that file with the project.
5. **Check every file before use.** Decode it (ffprobe or ffmpeg astats):
   right duration, no clipping (true peak below 0 dB), no long silence,
   no speech or music hiding under an effects label. Quiet files are
   common: a gain lift of 10 to 15 dB in the edit is normal, note it.
6. **Human listen before shipping.** An automated check proves a file is
   clean, not that it sounds right. The user listens to the final mix.

## Tested example (in examples/)

Three CC0 sounds found, verified and checked 2026-11-26 for a short
vertical tips video. Full Openverse records in examples/openverse-details.json.

- 01-typing-keyboard-clicks.mp3, "keyboard clicks" by ih8_snow, CC0 1.0,
  7.58 sec. Slice single clicks per typed letter, lift gain 10 to 15 dB.
- 02-pop-bubble-ui.mp3, "The Best Bubble Pop Sound For Game and UI" by
  el_boss, CC0 1.0, 0.31 sec. Hook pops and element pop ins, use as is.
- 03-payoff-chime-notification.mp3, "Chime Notification" by Jofae,
  CC0 1.0, 0.32 sec. Payoff and success moments, use as is.

Note: Openverse serves the Freesound preview MP3. For a final publish,
the original on Freesound is often WAV, listed under alt_files in the
detail record. For phone speaker SFX, the MP3 is fine.

## Games: sounding a game you built

Sound is half the game feel. Budget it from the start, not at the end.

1. Make the event list from your game code: every player action, every
   enemy or world event, every UI press. One row per event.
2. One sound per event to start. Short wins: most game SFX should be
   0.05 to 0.5 sec. Long tails muddy fast play.
3. Match the material: a wooden game wants wood taps and thuds, a space
   game wants clean electronic blips. Mixing real world foley into a
   pixel game usually sounds wrong.
4. Preload all sounds at start, play on the event, never fetch at play
   time. Keep a master volume and a mute toggle from day one.
5. Vary repeats: play a looping step or typing sound at slightly random
   pitch (0.95 to 1.05) so the ear does not hear a machine gun loop.

HTML / JavaScript (Web Audio):

```js
const sfx = {};
function loadSfx(name, url) {
  fetch(url).then(r => r.arrayBuffer()).then(buf =>
    audioCtx.decodeAudioData(buf)).then(decoded => { sfx[name] = decoded; });
}
function playSfx(name, rate = 1) {
  const src = audioCtx.createBufferSource();
  src.buffer = sfx[name];
  src.playbackRate.value = rate;
  src.connect(audioCtx.destination);
  src.start();
}
// loadSfx("jump", "sounds/jump.mp3"); then playSfx("jump", 0.97 + Math.random() * 0.06);
```

Python / pygame:

```python
import pygame
pygame.mixer.init()
sfx = {name: pygame.mixer.Sound(f"sounds/{name}.mp3")
       for name in ["jump", "coin", "hit", "win"]}
sfx["coin"].play()
```

Pyxel note: Pyxel plays its own chiptune SFX, so use Openverse sounds for
the trailer, menu video and cutscenes, and Pyxel's built in sounds in game.
Godot and Unity: drop the files into the project, one AudioStreamPlayer
or AudioSource per event, same event list rule.

## Prompts

Copy paste prompts that run this workflow well are in PROMPTS.md in this
folder, and as prompt 13 in the repo prompts/ folder.

## Rules

- CC0 first, CC BY only with its credit line shipped.
- Verify the license on the detail record, every time.
- CREDITS.md travels with the project, even for CC0 (credit is free).
- Nothing posts or publishes on the back of this skill without the
  user's approval of the exact final version.
