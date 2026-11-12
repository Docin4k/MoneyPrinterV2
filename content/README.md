# Script queue

Ready-made scripts for YouTube Shorts. When the queue is enabled in
`config.json`, every scheduled run takes the next unposted script from
`content/queue/` (in filename order), turns it into a video and uploads it.

```json
"script_queue": {"enabled": true, "dir": "content/queue", "when_empty": "skip"}
```

- `when_empty`: `"skip"` posts nothing when the queue runs out (recommended),
  `"llm"` lets the local Ollama model write a script instead.
- Posted scripts are recorded in `.mp/script_queue.json`. The files are never
  moved or deleted. To post a script again, remove its entry from that file.
- A script is only marked as posted after a successful upload, so a failed
  upload is retried on the next run.

## Script format

One JSON file per Short. Name files so they sort in the order you want them
posted, e.g. `013-pluto.json`.

```json
{
  "topic": "A day on Venus is longer than its year",
  "script": "On Venus, a single day lasts longer than an entire year. Venus spins so slowly that one full turn takes about 243 Earth days. ... Follow the channel for more.",
  "title": "A Day on Venus Is Longer Than Its Year #Venus #SpaceFacts #Shorts",
  "description": "Text for the YouTube description, including hashtags.",
  "last_sentence_is_cta": true,
  "scenes": [
    {"scene": "planet", "preset": "venus"},
    {"scene": "planet", "preset": "venus", "radius": 78, "y": 215},
    {"scene": "sun"},
    {"scene": "surface", "preset": "venus"},
    {"scene": "planet", "preset": "venus", "radius": 45},
    {"scene": "galaxy"}
  ]
}
```

| Field | Required | Meaning |
|---|---|---|
| `script` | yes | What the voice-over says. Each sentence becomes one shot, timed to how long it takes to say. |
| `title` | yes | YouTube title, 100 characters at most. |
| `description` | no | YouTube description. |
| `topic` | no | Short label, used to pick scenes when `scenes` is missing. |
| `last_sentence_is_cta` | no | `true` if the last sentence is a call to action; its footer says "FOLLOW FOR MORE" instead of a fact number. |
| `scenes` | no | One scene per sentence, for `"visual_style": "pixel_art"`. If missing or the count doesn't match the sentences, scenes are picked from keywords in each sentence. |
| `subtitle_fixes` | no | Regex replacements for the subtitles, e.g. `{"wonder\\s*bites": "WonderBytes"}`. |
| `music_style` | no | Chiptune style for this video: `adventure`, `chill`, `space ambient`, `march`, `waltz`, `funk`, `boss battle` or `music box`. If missing, the title picks one. The queue rotates them so neighbouring videos sound different. |

### Writing tips

- Keep sentences short; the on-screen headline fits about four lines.
- Write numbers as digits (`243`, `28000`). Years are read correctly
  (`1969` is spoken "nineteen sixty-nine"). Avoid decimals: write
  "two and a half" rather than `2.5`.
- Check every fact. These videos go out under your name.

## Scenes

| `scene` | Options |
|---|---|
| `planet` | `preset`: `venus`, `earth`, `mars`, `jupiter`, `saturn`, `neptune`, `uranus`, `moon`, `mercury`, `pluto`, `io`, `europa`, `titan`, `ganymede`, `triton`, `ceres`, `lava` (lava world), `ice` (ice world). Optional `radius` (pixels on the 180x320 canvas, default 58) and `y` (vertical centre, default 205). |
| `surface` | `preset`: `mars_day`, `mars_sunset`, `venus`, `moon`. Optional `rover`, `volcano`, `footprints` (true/false). |
| `sun` | The Sun with a flickering corona and a prominence. |
| `black_hole` | Black hole with a spinning accretion disk. |
| `pulsar` | Neutron star sweeping two beams. |
| `galaxy` | Rotating spiral galaxy. |
| `orbit` | The space station orbiting above Earth. |
| `diamond_rain` | Falling, sparkling diamonds. |
| `starfield` | Drifting stars; good for the closing call to action. |
| `comet` | A comet with a curved dust tail and a blue gas tail, pointing away from the Sun. |
| `asteroids` | Tumbling rocks drifting past at different distances. |
| `aurora` | Green and purple aurora curtains over a snowy forest. |
| `eclipse` | Total solar eclipse with a streaming corona. |
| `rocket` | A rocket launching through a dawn sky. |
| `supernova` | An expanding shockwave with glowing debris. |
| `nebula` | A colourful star-forming cloud with bright young stars. |
| `telescope` | A space telescope with a gold segmented mirror and sunshield. |
| `binary_suns` | Two suns circling above desert dunes. |

Underwater scenes (from `src/pixel_ocean.py`): `deep_sea`, `anglerfish`,
`jellyfish`, `whale`, `octopus`, `coral_reef`, `shark`, `shipwreck`, `vent`,
`submarine`, `squid`, `ocean_surface`, `trench`, `fish_school`, `sea_turtle`,
`kelp_forest`. See `content/WRITING_GUIDE.md` for what each shows.
