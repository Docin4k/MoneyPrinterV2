"""Queue of ready-made Shorts scripts.

Scripts are JSON files in the queue folder (default: content/queue), used in
filename order. Which ones have been posted is recorded in .mp/script_queue.json,
so the script files themselves never move and git stays clean.

See content/README.md for the script format.
"""
import json
import os
from datetime import datetime

from config import ROOT_DIR, get_script_queue

STATE_PATH = os.path.join(ROOT_DIR, ".mp", "script_queue.json")
REQUIRED_FIELDS = ("script", "title")


def queue_dir() -> str:
    folder = get_script_queue()["dir"]
    return folder if os.path.isabs(folder) else os.path.join(ROOT_DIR, folder)


def _load_state() -> dict:
    if not os.path.exists(STATE_PATH):
        return {"posted": {}}
    with open(STATE_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def _save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as file:
        json.dump(state, file, indent=2)


def load_script(path: str) -> dict:
    """Read and validate one script file."""
    with open(path, "r", encoding="utf-8") as file:
        spec = json.load(file)
    missing = [field for field in REQUIRED_FIELDS if not spec.get(field)]
    if missing:
        raise ValueError(f"{os.path.basename(path)} is missing: {', '.join(missing)}")
    if len(spec["title"]) > 100:
        raise ValueError(f"{os.path.basename(path)}: title is over YouTube's 100-character limit")
    return spec


def pending() -> list[str]:
    """Script filenames not yet posted, in order."""
    folder = queue_dir()
    if not os.path.isdir(folder):
        return []
    posted = _load_state()["posted"]
    return sorted(name for name in os.listdir(folder) if name.endswith(".json") and name not in posted)


def next_script() -> tuple[str, dict] | None:
    """The next unposted script as (filename, spec), or None if the queue is empty."""
    for name in pending():
        return name, load_script(os.path.join(queue_dir(), name))
    return None


def mark_posted(name: str, title: str, video_path: str = "") -> None:
    """Record that a script was uploaded, so it is not used again."""
    state = _load_state()
    state["posted"][name] = {
        "title": title,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "video_path": video_path,
    }
    _save_state(state)
