"""Fill in config.json for the WonderBytes setup, so nothing has to be edited by hand.

Run from the project folder:
    python scripts/mac/configure_wonderbytes.py

- Creates config.json from config.example.json if it doesn't exist yet.
- Finds the Firefox profile named "wonderbytes" (or uses the path you give
  with --profile "/Users/you/Library/.../abcd1234.wonderbytes").
- Sets the pixel-art style, chiptune music, Bella voice, script queue and
  the other WonderBytes settings. Everything else in config.json is kept.
- Keeps headless off so you can watch the first upload; use --headless
  once uploads work.
"""
import argparse
import glob
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG = os.path.join(ROOT, "config.json")
EXAMPLE = os.path.join(ROOT, "config.example.json")
PROFILES = os.path.expanduser("~/Library/Application Support/Firefox/Profiles")

parser = argparse.ArgumentParser(description="Configure MoneyPrinterV2 for WonderBytes.")
parser.add_argument("--profile", help="Firefox profile folder (found automatically if omitted)")
parser.add_argument("--profile-name", default="wonderbytes", help="Firefox profile name to look for")
parser.add_argument("--headless", action="store_true", help="hide Firefox during uploads")
args = parser.parse_args()

if not os.path.exists(CONFIG):
    shutil.copy(EXAMPLE, CONFIG)
    print("Created config.json from config.example.json")

try:
    with open(CONFIG, encoding="utf-8") as f:
        config = json.load(f)
except json.JSONDecodeError as e:
    sys.exit(
        f"config.json has a mistake on line {e.lineno} ({e.msg}).\n"
        "Easiest fix: start fresh with\n"
        "    cp config.example.json config.json\n"
        "and run this script again."
    )

profile = args.profile
if not profile:
    # Profile folders are "<random>.<name>"; match the name ignoring capitals
    wanted = args.profile_name.lower()
    matches = sorted(p for p in glob.glob(os.path.join(PROFILES, "*"))
                     if os.path.isdir(p) and os.path.basename(p).split(".", 1)[-1].lower() == wanted)
    if not matches:
        found = [os.path.basename(p) for p in glob.glob(os.path.join(PROFILES, "*"))]
        sys.exit(
            f"Couldn't find a Firefox profile named '{args.profile_name}' in\n  {PROFILES}\n"
            f"Profiles found: {', '.join(found) or 'none'}\n"
            "Create it in Firefox at about:profiles (Part 3, step 6), or pass the path with --profile."
        )
    profile = matches[0]
if not os.path.isdir(profile):
    sys.exit(f"That Firefox profile folder doesn't exist:\n  {profile}")

config.update({
    "firefox_profile": profile,
    "headless": bool(args.headless),
    "ollama_model": config.get("ollama_model") or "llama3.2:3b",
    "tts_voice": "Bella",
    "visual_style": "pixel_art",
    "music_source": "chiptune",
    "music_volume": 0.15,
    "subtitle_replacements": {"wonder\\s*bites": "WonderBytes"},
    "script_queue": {"enabled": True, "dir": "content/queue", "when_empty": "skip"},
})

with open(CONFIG, "w", encoding="utf-8") as f:
    json.dump(config, f, indent=2)
    f.write("\n")

print("config.json is ready:")
for key in ("firefox_profile", "headless", "tts_voice", "visual_style", "music_source", "script_queue"):
    print(f"  {key}: {json.dumps(config[key])}")
