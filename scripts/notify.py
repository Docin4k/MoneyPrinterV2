"""Send a phone notification about one scheduled run, via ntfy (https://ntfy.sh).

Called by scripts/mac/run_youtube.sh after each run:

    python scripts/notify.py <log file> <byte offset where this run started>

It reads that run's part of the log and sends one short message: posted (with
the title and link), failed (with the reason), queue empty, or test video made.

Set up: install the free ntfy app on your phone, subscribe to a topic name
that only you know, and put the same name in config.json:

    "ntfy_topic": "mpv2-abc123xyz"

Without "ntfy_topic" this does nothing. Send a test with:

    python scripts/notify.py --test
"""
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(path, default):
    try:
        with open(os.path.join(ROOT, path), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def send(topic, title, message, tags="", priority="default", click=None, server="https://ntfy.sh"):
    headers = {"Title": title.encode("ascii", "ignore").decode(), "Priority": priority}
    if tags:
        headers["Tags"] = tags
    if click:
        headers["Click"] = click
    req = urllib.request.Request(f"{server.rstrip('/')}/{topic}", data=message.encode("utf-8"), headers=headers)
    urllib.request.urlopen(req, timeout=20).read()


def summarize(text, channel):
    """(title, message, tags, priority, click) for one run's log text, or None."""
    script = re.search(r"Using queued script: (\S+)", text)
    video_title = ""
    if script:
        spec = _load(os.path.join("content", "queue", script.group(1)), {})
        video_title = spec.get("title", "").split("#")[0].strip()
    url = re.search(r"Uploaded Video: (\S+)", text)

    if "Uploaded Short." in text:
        msg = video_title or "New Short"
        if url:
            msg += f"\n{url.group(1)}"
        if "Cross-posted via Post Bridge" in text:
            msg += "\nAlso posted to Instagram via Post Bridge."
        else:
            cross = re.search(r"(Post Bridge cross-post failed: .+|No Post Bridge accounts were resolved.*|"
                              r"Post Bridge is enabled but no API key.*)", text)
            if cross:
                msg += f"\nInstagram: {cross.group(1)[:200]}"
        return f"{channel} posted a Short", msg, "white_check_mark", "default", url.group(1) if url else None
    if "Generated (not uploaded)" in text:
        return f"{channel} test video made", video_title or "Test video ready (not uploaded).", "test_tube", "low", None
    if "Script queue is empty" in text:
        return f"{channel}: queue is empty", "No scripts left to post. Add more scripts to the queue.", \
            "warning", "high", None
    failed = re.search(r"YouTube upload failed: (.+)", text)
    if failed:
        return f"{channel} upload failed", f"{video_title}\n{failed.group(1)[:300]}".strip(), "x", "high", None
    lines = [l.strip() for l in text.splitlines() if l.strip() and not l.startswith(("=====", "Exit code"))]
    exit_code = re.search(r"Exit code: (\d+)", text)
    if exit_code and exit_code.group(1) != "0":
        last = lines[-1] if lines else "unknown error"
        return f"{channel} run crashed", f"{video_title}\n{last[:300]}".strip(), "x", "high", None
    return None


def main():
    config = _load("config.json", {})
    topic = config.get("ntfy_topic")
    if not topic:
        return
    server = config.get("ntfy_server", "https://ntfy.sh")
    channel = _load(os.path.join("content", "channel.json"), {}).get("name", "MoneyPrinter")

    if sys.argv[1:2] == ["--test"]:
        send(topic, f"{channel} notifications are on", "You'll get a message here after every upload.",
             "tada", server=server)
        print(f"Sent a test notification to ntfy topic '{topic}'.")
        return

    log_path, offset = sys.argv[1], int(sys.argv[2])
    with open(log_path, "rb") as f:
        f.seek(offset)
        text = f.read().decode("utf-8", "replace")
    # Strip terminal colour codes
    text = re.sub(r"\x1b\[[0-9;]*m", "", text)
    result = summarize(text, channel)
    if result:
        title, message, tags, priority, click = result
        send(topic, title, message, tags, priority, click, server)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # a notification problem must never break the run
        print(f"Notification not sent: {e}")
