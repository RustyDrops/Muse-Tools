# Prompts for using Kenney assets the easy way

The rule behind every prompt: never hand-tune a scale number. Kenney kits are authored at roughly half scale and each kit disagrees about a metre. Measure the model, fit it to a real world size, ground it. The tools in `tools/` do that; the prompts tell an agent to use them.

## 1. Build a scene from a Kenney pack

```text
Build a Three.js scene using only assets from the Kenney pack in <folder>.
First run: python3 tools/make-manifest.py <glb-folder> <comma list of model names> manifest.json
Then load the scene with tools/kenney-fit.js loadScene(): every model is
scaled by its manifest fit target and grounded, no scale numbers in scene code.
Place furniture with a placements map (at: [x, z], rotY, on: "host" for items
that sit on furniture). Add a 1 m grid floor and a 2 m reference pole banded
every 0.5 m so scale can be checked visually. Capture a screenshot, view it
yourself, and report: what loaded, each model's final measured height, and
anything floating, sunk, or overlapping. Do not call it done from code alone.
```

## 2. Add one new asset to an existing scene

```text
Add the Kenney model <name>.glb to this scene. If it has no fit target in
tools/make-manifest.py TARGETS, add one first: pick the real world size of
that object (a chair back is about 0.9 m, a desk top 0.75 m, a floor lamp
about 1.5 m) and say why. Regenerate manifest.json, place the model with
loadScene() placements, never with a hand-typed scale. If it sits on another
piece of furniture, use on: "<host name>". Re-run the gate checks and the
screenshot, and show me the model's final measured size next to its target.
```

## 3. Fix a scale or placement problem

```text
In this Kenney scene, <describe the problem: floating / sunk / too big /
overlapping>. Change one thing only: the fit target in make-manifest.py,
the placement entry, or the kenney-fit.js helper, whichever actually owns
the problem. Regenerate, recapture, view the screenshot, and compare against
the previous version. Report which gate failed before and passes now, with
measured numbers, not impressions.
```

## 4. QA any Kenney scene before calling it done

```text
QA this Kenney scene against these gates and report pass or fail per gate
with measured evidence: (1) every manifest asset loaded, zero errors;
(2) every grounded model's final size within 2 percent of its target and its
base at y = 0 within 0.01 m; (3) stacked items sit on their host's top within
0.02 m; (4) no grounded footprints overlap (rug excluded); (5) scripted input
moves the player at least 1 m and collects an orb; (6) you viewed the final
screenshot and every asset is visible, grounded, and in proportion next to
the 0.5 m banded pole. A gate you did not measure is a failed gate.
```

## 5. Turn a room description into a layout

```text
Turn this room description into a placements map for the Kenney scene:
<description>. Use only models already in manifest.json. Keep walkways at
least 0.8 m wide, put tall items (1.7 m plus) against the back wall, seat
height items in the middle, and anything that sits on furniture as on: entries.
Return the placements map plus one line per item saying where it went and why.
Do not change any fit targets.
```

## Sizes cheat sheet (real world targets that work)

Chair back 0.9 m, desk chair 0.92 m, dining or desk height 0.75 m, coffee table 0.45 m, sofa back 0.85 m, TV stand 0.62 m, TV screen 0.6 m tall, tall bookcase 1.8 m, single bed 0.55 m tall and about 2 m long, floor lamp 1.55 m, laptop 0.34 m wide, rug 3.2 m long side. When in doubt, measure the real object, not the model.
