"""Tools for the script queue in content/queue.

Run from the project folder:

    python scripts/queue_tools.py check             # validate every script in the queue
    python scripts/queue_tools.py topics            # list every topic/title already used
    python scripts/queue_tools.py add new.json      # validate, number and add new scripts

`add` takes a JSON list of scripts, each like:

    {"slug": "pluto-heart",
     "topic": "Pluto's heart",
     "sentences": ["Five fact sentences...", "...", "...", "...", "..."],
     "title": "Pluto Has a Giant Heart #Pluto #SpaceFacts #Shorts",
     "description": "One or two sentences for YouTube.",
     "hashtags": "#Pluto #Space #ScienceFacts #Shorts",
     "scenes": ["planet:pluto", "planet:pluto:75:215", "rocket", "sun", "planet:moon"]}

Scene shorthand: "planet:<preset>[:radius[:y]]", "surface:<preset>[:rover|:volcano|:footprints]",
or a scene name (see content/README.md). The call to action sentence, its scene and
a music style (rotating so neighbours differ) are added automatically. Nothing is
written unless every new script passes validation.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = os.path.join(ROOT, "content", "queue")
sys.path.insert(0, os.path.join(ROOT, "src"))
import pixel_art as pa  # noqa: E402
from chiptune import STYLES  # noqa: E402

# Channel details (name, call to action) live in content/channel.json
CHANNEL = json.load(open(os.path.join(ROOT, "content", "channel.json")))
CTA = CHANNEL["cta"]
# Scenes for the closing call to action, rotating (set "cta_scenes" in channel.json)
CTA_SCENES = CHANNEL.get("cta_scenes", ["starfield", "nebula", "galaxy", "comet"])


def split_sentences(script: str) -> list:
    return [s for s in re.split(r"(?<=[.!?])\s+", script.strip()) if s.strip()]


def parse_scene(short) -> dict:
    if isinstance(short, dict):
        return short
    parts = short.split(":")
    if parts[0] == "planet":
        scene = {"scene": "planet", "preset": parts[1]}
        if len(parts) > 2:
            scene["radius"] = int(parts[2])
        if len(parts) > 3:
            scene["y"] = int(parts[3])
        return scene
    if parts[0] == "surface":
        scene = {"scene": "surface", "preset": parts[1]}
        for flag in parts[2:]:
            scene[flag] = True
        return scene
    return {"scene": parts[0]}


def queue_files() -> list:
    return sorted(f for f in os.listdir(QUEUE) if f.endswith(".json"))


def validate(name: str, spec: dict) -> list:
    """Problems with one finished script spec (empty list if fine)."""
    problems = []
    sentences = split_sentences(spec.get("script", ""))
    scenes = spec.get("scenes", [])
    if not spec.get("title"):
        problems.append("missing title")
    elif len(spec["title"]) > 100:
        problems.append(f"title is {len(spec['title'])} characters (max 100)")
    if len(sentences) < 3:
        problems.append(f"only {len(sentences)} sentences")
    if scenes and len(scenes) != len(sentences):
        problems.append(f"{len(scenes)} scenes for {len(sentences)} sentences")
    for scene in scenes:
        kind = scene.get("scene")
        if kind not in pa.SCENES:
            problems.append(f"unknown scene '{kind}'")
        elif kind == "planet" and scene.get("preset") not in pa.PLANET_PRESETS:
            problems.append(f"unknown planet '{scene.get('preset')}'")
        elif kind == "surface" and scene.get("preset") not in pa.SURFACE_PRESETS:
            problems.append(f"unknown surface '{scene.get('preset')}'")
    missing = sorted({c for c in spec.get("script", "").upper() if c not in pa.GLYPHS})
    if missing:
        problems.append(f"characters the pixel font lacks: {missing}")
    if spec.get("music_style") and spec["music_style"] not in STYLES:
        problems.append(f"unknown music_style '{spec['music_style']}'")
    for s in sentences:
        if len(s.split()) > 28:
            problems.append(f"sentence too long to read in time: {s[:50]}...")
    return [f"{name}: {p}" for p in problems]


def cmd_check() -> int:
    problems = []
    for f in queue_files():
        problems += validate(f, json.load(open(os.path.join(QUEUE, f))))
    print("\n".join(problems) if problems else f"all {len(queue_files())} scripts valid")
    return 1 if problems else 0


def cmd_topics() -> int:
    for f in queue_files():
        spec = json.load(open(os.path.join(QUEUE, f)))
        print(f"{f[:-5]:42} | {spec.get('topic', '')} | {spec['title'].split('#')[0].strip()}")
    return 0


def cmd_add(path: str) -> int:
    new = json.load(open(path))
    files = queue_files()
    next_num = max((int(f.split("-", 1)[0]) for f in files), default=0) + 1
    used_slugs = {f.split("-", 1)[1][:-5] for f in files}
    used_titles = {json.load(open(os.path.join(QUEUE, f)))["title"].split("#")[0].strip().lower() for f in files}
    last_style = json.load(open(os.path.join(QUEUE, files[-1]))).get("music_style") if files else None
    styles = list(STYLES)

    out, problems = [], []
    for i, item in enumerate(new):
        slug = re.sub(r"[^a-z0-9-]+", "-", item["slug"].lower()).strip("-")
        name = f"{next_num + i:03d}-{slug}.json"
        if slug in used_slugs:
            problems.append(f"{name}: slug already used")
        if item["title"].split("#")[0].strip().lower() in used_titles:
            problems.append(f"{name}: title already used")
        sentences = item["sentences"]
        scenes = [parse_scene(s) for s in item["scenes"]]
        if len(scenes) != len(sentences):
            problems.append(f"{name}: {len(scenes)} scenes for {len(sentences)} sentences")
        style = styles[(styles.index(last_style) + 1 + i * 3) % len(styles)] if last_style in styles else styles[i % len(styles)]
        prev = out[-1][1]["music_style"] if out else last_style
        if style == prev:
            style = styles[(styles.index(style) + 1) % len(styles)]
        spec = {
            "topic": item["topic"],
            "script": " ".join(sentences + [CTA]),
            "title": item["title"],
            "description": f"{item['description']}\n\n{CTA}\n\n{item['hashtags']}",
            "last_sentence_is_cta": True,
            "scenes": scenes + [{"scene": CTA_SCENES[(next_num + i) % len(CTA_SCENES)]}],
            "music_style": style,
        }
        problems += validate(name, spec)
        used_slugs.add(slug)
        out.append((name, spec))

    if problems:
        print("Not added; fix these first:\n" + "\n".join(problems))
        return 1
    for name, spec in out:
        with open(os.path.join(QUEUE, name), "w") as f:
            json.dump(spec, f, indent=2)
            f.write("\n")
        print("added", name, f"({spec['music_style']})")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("check", "topics", "add"):
        print(__doc__)
        sys.exit(2)
    if sys.argv[1] == "add":
        sys.exit(cmd_add(sys.argv[2]))
    sys.exit(cmd_check() if sys.argv[1] == "check" else cmd_topics())
