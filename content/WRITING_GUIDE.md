# Writing WonderBytes scripts

Rules for anyone adding scripts to `content/queue/`, including the weekly
automated writing session. Add scripts with `scripts/queue_tools.py add`,
which validates and numbers them; never hand-number files.

## The channel

- **WonderBytes:** surprising science and space facts, "facts that sound fake
  but are true".
- Videos are 30–50 second YouTube Shorts with no voice-over: captions, 8-bit
  pixel-art scenes and chiptune music.

## Each script

- **One topic, one hook.** The first sentence is the most surprising claim,
  stated plainly ("On Venus, a single day lasts longer than an entire year.").
- **Exactly five fact sentences**, each under about 20 words, each adding
  something new. The tool appends the call to action.
- **Facts must be true and current.** Only use facts that are well established
  and that you are confident of. Round numbers sensibly ("about 2,000 km/h").
  When science is unsure, say so ("may", "scientists think"). Never invent
  numbers, quotes or events. Skip a topic rather than guess.
- **Avoid dates that will age** ("this year", "recently"); give the year.
- **Plain characters only:** letters, digits, `. , ' ! ? - : ; / % & ( ) #`.
  No quotes other than `'`, no accents (write "Bootes", not "Boötes").
- **Title** under 100 characters, a short punchy claim plus 2–3 hashtags ending
  with `#Shorts`. **Description:** one or two sentences restating the facts.
- **Scenes:** one per sentence, from the list in `content/README.md`. Prefer a
  scene that shows what the sentence is about, and vary the framing
  (e.g. `planet:jupiter`, `planet:jupiter:80:225`, `planet:jupiter:45:200`).
- **Stat and gauge (shown on screen the whole video).** WonderBytes uses the
  "HUD" layout: a short `stat` bar under the title and an animated `gauge` in
  the corner.
  - `stat`: the key number or claim in a few words, at most 52 characters,
    e.g. `"ONE LAP EVERY 90 MINUTES"`. It should add something the title
    doesn't already say.
  - `gauge`: `{"label": "SPEED", "value": 28000, "max": 30000, "unit": "KM/H"}`.
    The needle sweeps up to `value` out of `max`. Pick something the video
    is about (speed, temperature, distance, size, time, a percentage), keep
    the unit short (`KM/H`, `C`, `LY`, `KM`, `MIN`, `%`) and the label at most
    11 characters. Values can't be negative (no gauge for "minus 180 C").
  - **Both must use numbers already stated in the script's facts.** Never add
    a number just for the gauge. If no fact has a good number, leave `gauge`
    out (the stat alone is fine).
- **Not a repeat.** Check `python scripts/queue_tools.py topics` first; don't
  reuse a topic or a fact that is the main point of an existing video.

## Topic ideas

Planets and moons, the Sun and other stars, black holes and neutron stars,
galaxies and the universe, comets and asteroids, space missions and their
history, astronauts' lives in space, telescopes and discoveries, physics that
shows up in space (light, gravity, time), and Earth as a planet.

## Batch file format

```json
[
  {"slug": "venus-day",
   "topic": "A day on Venus is longer than its year",
   "sentences": ["...", "...", "...", "...", "..."],
   "title": "A Day on Venus Is Longer Than Its Year #Venus #SpaceFacts #Shorts",
   "description": "One or two sentences.",
   "hashtags": "#Venus #Space #Astronomy #ScienceFacts #Shorts",
   "scenes": ["planet:venus", "planet:venus:78:215", "sun", "surface:venus", "planet:venus:45:200"],
   "stat": "SPINS BACKWARDS: SUN RISES IN THE WEST",
   "gauge": {"label": "ONE SPIN", "value": 243, "max": 300, "unit": "DAYS"}}
]
```

Then:

```bash
python scripts/queue_tools.py add batch.json
python scripts/queue_tools.py check
```
