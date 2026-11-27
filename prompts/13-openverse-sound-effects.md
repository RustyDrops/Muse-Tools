# 13 - Add free, licensed sound effects (Openverse)

Hand this to your Muse when a video, game or app needs sound and you do
not want to pay for a library or risk an unlicensed file.

> Add sound effects from Openverse to [my video / game / app at path].
>
> 1. First list the sound jobs: every moment or event that needs a sound.
>    For a video: hook, typing, transitions, reveals, payoff. For a game:
>    player actions, pickups, hits, win and lose, UI presses. Show me the
>    list before searching.
> 2. Search Openverse (api.openverse.org) per job with short concrete
>    words. CC0 only unless I approve CC BY for a specific sound.
> 3. Verify each license on the sound's Openverse detail record, not the
>    search snippet. Download into a sounds/ folder in the project.
> 4. Check each file: duration, no clipping, no long silence, no speech
>    or music hiding in an effects file. Note any gain lift needed.
> 5. Write CREDITS.md: title, creator, license, license link, source link
>    for every sound, even CC0 ones.
> 6. Wire them in: preload, play on the event or moment, a mute or volume
>    control where the platform supports it. For repeating sounds, vary
>    pitch slightly (0.95 to 1.05).
> 7. Stop and show me the job to sound map and the credits before anything
>    is published. No generative audio.

The full workflow, a tested tool and worked examples live in the
`openverse-sfx/` folder of this repo.
