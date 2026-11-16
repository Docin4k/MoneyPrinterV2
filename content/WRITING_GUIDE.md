# Writing DinoBytes scripts

Rules for anyone adding scripts to `content/queue/`, including the weekly
automated writing session. Add scripts with `scripts/queue_tools.py add`,
which validates and numbers them; never hand-number files.

## The channel

- **DinoBytes:** dinosaurs and prehistoric life, "prehistoric facts, pixel by
  pixel": dinosaurs, flying and sea reptiles, ice age giants, early life,
  fossils and how we know what we know.
- Videos are YouTube Shorts of a minute or a little more with no voice-over:
  captions, 8-bit pixel-art scenes and chiptune music.

## Each script

- **One topic, one hook.** The first sentence is the most surprising claim,
  stated plainly ("Stegosaurus lived closer in time to us than to T. rex.").
- **Exactly six fact sentences**, each under about 20 words, each adding
  something new. The tool appends the call to action.
- **Facts must be true and current.** Paleontology changes as new fossils are
  found, so only use well-established findings, give sizes as rough ranges
  ("about 12 meters"), and hedge estimates ("scientists estimate", "may",
  "probably"). Never invent numbers, quotes or discoveries. Skip a topic
  rather than guess.
- **Name things correctly.** Pterosaurs, mosasaurs, plesiosaurs, ichthyosaurs,
  mammoths and saber-toothed cats are **not** dinosaurs; birds **are**.
  Avoid popular myths (T. rex could only see movement, dinosaurs lived with
  cavemen, all dinosaurs were huge, Brontosaurus "never existed").
- **Avoid dates that will age** ("this year", "recently"); give the year.
- **Plain characters only:** letters, digits, `. , ' ! ? - : ; / % & ( ) #`.
  No quotes other than `'`, no accents.
- **Title** under 100 characters, a short punchy claim plus 2-3 hashtags ending
  with `#Shorts`. **Description:** one or two sentences restating the facts.
- **Scenes:** one per sentence (six), from the list below. Prefer the scene
  that shows what the sentence is about; neighbouring sentences can repeat a
  scene (each animates differently over time).
- **Stat and gauge (shown on screen the whole video).** DinoBytes uses the
  "HUD" layout: a short `stat` bar under the title and an animated `gauge` in
  the corner.
  - `stat`: the key number or claim in a few words, at most 52 characters.
    It should add something the title doesn't already say.
  - `gauge`: `{"label": "LENGTH", "value": 12, "max": 15, "unit": "M"}`.
    The needle sweeps up to `value` out of `max`. Good gauges: length,
    weight (`TONNES`), height, speed (`KM/H`), age (`M YRS` for millions of
    years ago), teeth. Label at most 11 characters, unit short.
  - **Both must use numbers already stated in the script's facts.** Never add
    a number just for the gauge. If no fact has a good number, leave `gauge`
    out (the stat alone is fine).
- **Not a repeat.** Check `python scripts/queue_tools.py topics` first; don't
  reuse a topic or a fact that is the main point of an existing video.

## Scenes

| Scene | Shows |
|---|---|
| `trex` | A Tyrannosaurus striding through ferns, jaws snapping |
| `sauropod` | A long-necked sauropod browsing a tall tree, another behind |
| `triceratops` | A Triceratops with frill and three horns |
| `stegosaurus` | A Stegosaurus with back plates and a swinging spiked tail |
| `raptor` | A small feathered dromaeosaur (Velociraptor-sized) running |
| `pterosaur` | Pterosaurs soaring over a sea cliff at dusk |
| `mosasaur` | A mosasaur swimming past ammonites |
| `plesiosaur` | A long-necked plesiosaur rowing through fish |
| `mammoth` | A woolly mammoth in falling snow |
| `impact` | The asteroid streaking in, then a flash and blast wave |
| `fossil` | A skeleton in layers of rock with a brush sweeping dust |
| `eggs` | A nest of dinosaur eggs, one hatching |
| `amber` | A glowing drop of amber with an insect inside |
| `volcano` | An erupting volcano over a prehistoric forest |
| `cambrian` | The Cambrian sea floor: trilobites and a big predator |

The scenes take an optional mood for land scenes: `{"scene": "trex", "mood": "dusk"}`
(`day` or `dusk`). Space scenes (`planet:earth`, `asteroids`, ...) and ocean
scenes (`deep_sea`, `fish_school`, ...) also work.

## Topic ideas

Famous dinosaurs and surprising details about them, the biggest and smallest,
feathers and the dinosaur-bird link, eggs and babies, flying and swimming
reptiles, the asteroid and the mass extinctions, ice age animals, early life
(Cambrian, giant insects), how fossils form and how scientists date them,
famous fossil finds and the people who made them.

## Batch file format

```json
[
  {"slug": "trex-bite",
   "topic": "T. rex had the strongest bite of any land animal",
   "sentences": ["...", "...", "...", "...", "...", "..."],
   "title": "T. rex Could Crush Bone #TRex #Dinosaurs #Shorts",
   "description": "One or two sentences.",
   "hashtags": "#TRex #Dinosaurs #Paleontology #DinoFacts #Shorts",
   "scenes": ["trex", "trex", "fossil", "trex", "trex", "trex"],
   "stat": "TEETH THE SIZE OF BANANAS",
   "gauge": {"label": "LENGTH", "value": 12, "max": 15, "unit": "M"}}
]
```

Then:

```bash
python scripts/queue_tools.py add batch.json
python scripts/queue_tools.py check
```
