"""Turn on Instagram (and TikTok) cross-posting through Post Bridge for this channel.

Run from the channel's folder (each channel has its own config.json):

    venv/bin/python scripts/setup_post_bridge.py          # set up or change
    venv/bin/python scripts/setup_post_bridge.py --off    # stop cross-posting

It asks for your Post Bridge API key (typed hidden, saved only in this
folder's config.json), lists the accounts connected to Post Bridge, lets you
pick the one(s) for this channel, and switches on automatic cross-posting
after every successful YouTube upload.
"""
import getpass
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from classes.PostBridge import PostBridge, PostBridgeClientError  # noqa: E402

CONFIG = os.path.join(ROOT, "config.json")


def main():
    with open(CONFIG, encoding="utf-8") as f:
        config = json.load(f)
    pb = config.get("post_bridge") or {}
    try:
        with open(os.path.join(ROOT, "content", "channel.json"), encoding="utf-8") as f:
            channel = json.load(f).get("name", "this channel")
    except (OSError, ValueError):
        channel = "this channel"

    if "--off" in sys.argv:
        pb["enabled"] = False
        pb["auto_crosspost"] = False
        config["post_bridge"] = pb
        save(config)
        print(f"Cross-posting is off for {channel}.")
        return

    key = pb.get("api_key") or os.environ.get("POST_BRIDGE_API_KEY", "")
    if key:
        answer = input("A Post Bridge API key is already saved. Use it? (Y/n): ").strip().lower()
        if answer in ("n", "no"):
            key = ""
    while not key:
        key = getpass.getpass("Paste your Post Bridge API key (it stays hidden), then press Return: ").strip()

    try:
        accounts = PostBridge(key).list_social_accounts(platforms=["instagram", "tiktok"])
    except PostBridgeClientError as e:
        sys.exit(f"Post Bridge didn't accept that: {e}\nCheck the API key and run this again.")

    if not accounts:
        sys.exit("No Instagram or TikTok accounts are connected to Post Bridge yet.\n"
                 "Connect them at post-bridge.com, then run this again.")

    print(f"\nAccounts connected to Post Bridge:")
    for i, a in enumerate(accounts, 1):
        print(f"  {i}. {a.get('platform', '?'):10} @{a.get('username', '?')}")
    picks = []
    while not picks:
        raw = input(f"\nWhich should {channel} post to? Numbers separated by commas (e.g. 1 or 1,3): ")
        try:
            picks = sorted({int(x) for x in raw.replace(" ", "").split(",") if x})
            if not all(1 <= p <= len(accounts) for p in picks):
                raise ValueError
        except ValueError:
            print("Please type numbers from the list.")
            picks = []

    chosen = [accounts[p - 1] for p in picks]
    config["post_bridge"] = {
        "enabled": True,
        "api_key": key,
        "platforms": sorted({a.get("platform") for a in chosen if a.get("platform")}),
        "account_ids": [a["id"] for a in chosen],
        "auto_crosspost": True,
    }
    save(config)
    names = ", ".join(f"{a.get('platform')} @{a.get('username', '?')}" for a in chosen)
    print(f"\nDone. After each YouTube upload, {channel} will also post to: {names}")


def save(config):
    with open(CONFIG, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()
