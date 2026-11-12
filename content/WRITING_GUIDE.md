# Writing Pixel Abyss scripts

Rules for anyone adding scripts to `content/queue/`, including the weekly
automated writing session. Add scripts with `scripts/queue_tools.py add`,
which validates and numbers them; never hand-number files.

## The channel

- **Pixel Abyss:** strange deep sea and ocean facts, "weird true facts from
  the deep".
- Videos are 30-50 second YouTube Shorts with no voice-over: captions, 8-bit
  pixel-art underwater scenes and chiptune music.

## Each script

- **One topic, one hook.** The first sentence is the most surprising claim,
  stated plainly ("An octopus has three hearts.").
- **Exactly five fact sentences**, each under about 20 words, each adding
  something new. The tool appends the call to action.
- **Facts must be true and current.** Only use facts that are well established
  and that you are confident of. Round numbers sensibly ("about 2,000 meters").
  When science is unsure, say so ("may", "scientists think"). Never invent
  numbers, quotes or events. Skip a topic rather than guess. Watch for popular
  myths (goldfish memory, "we know more about Mars than the ocean floor",
  exact percentages of the ocean "unexplored"): leave them out unless you can
  state them precisely.
- **Avoid dates that will age** ("this year", "recently"); give the year.
- **Plain characters only:** letters, digits, `. , ' ! ? - : ; / % & ( ) #`.
  No quotes other than `'`, no accents, no degree sign (write "degrees
  Celsius").
- **Title** under 100 characters, a short punchy claim plus 2-3 hashtags ending
  with `#Shorts`. **Description:** one or two sentences restating the facts.
- **Scenes:** one per sentence, from the underwater list below. Prefer the
  scene that shows what the sentence is about; neighbouring sentences can
  repeat a scene (each one animates differently over time).
- **Not a repeat.** Check `python scripts/queue_tools.py topics` first; don't
  reuse a topic or a fact that is the main point of an existing video.

## Scenes

| Scene | Shows |
|---|---|
| `deep_sea` | Dark midwater: marine snow, blinking lights, lanternfish, a glowing siphonophore |
| `anglerfish` | An anglerfish with its glowing lure in pitch black water |
| `jellyfish` | Glowing jellyfish pulsing upward |
| `whale` | A huge whale gliding through sunlit water, little fish for scale |
| `octopus` | An octopus on the sea floor, changing colour, waving its arms |
| `coral_reef` | Bright reef: corals, sea fan, anemone with a clownfish, reef fish |
| `shark` | A shark cruising through open blue water with pilot fish |
| `shipwreck` | A sunken wooden ship with broken masts, bubbles, seaweed |
| `vent` | A hydrothermal vent: black smoker chimney, tube worms, a crab |
| `submarine` | A research submersible with its headlight on, descending |
| `squid` | A giant squid with its huge eye and long tentacles |
| `ocean_surface` | Split view: sky, sun and waves above, sunlit water below |
| `trench` | Cross-section of a deep trench with a tiny sub going down |
| `fish_school` | A swirling ball of silver fish and a dolphin |
| `sea_turtle` | A sea turtle swimming with slow flipper strokes |
| `kelp_forest` | Tall swaying kelp, a sea otter at the surface, fish |

The space scenes from WonderBytes (`planet:earth`, `aurora`, `sun`, ...) also
work, e.g. `planet:earth` for a sentence about the whole planet.

## Topic ideas

Deep sea creatures and their adaptations, bioluminescence, whales and
dolphins, sharks and rays, octopuses and squid, jellyfish, coral reefs, kelp
forests, sea turtles and seabirds, trenches and the sea floor, hydrothermal
vents, ocean exploration and submersibles, famous shipwrecks, tides, waves and
currents, and the ocean's role in Earth's climate and oxygen.

## Batch file format

```json
[
  {"slug": "octopus-three-hearts",
   "topic": "Octopuses have three hearts and blue blood",
   "sentences": ["...", "...", "...", "...", "..."],
   "title": "Octopuses Have Three Hearts and Blue Blood #Octopus #Ocean #Shorts",
   "description": "One or two sentences.",
   "hashtags": "#Octopus #Ocean #MarineBiology #OceanFacts #Shorts",
   "scenes": ["octopus", "octopus", "octopus", "octopus", "octopus"]}
]
```

Then:

```bash
python scripts/queue_tools.py add batch.json
python scripts/queue_tools.py check
```
