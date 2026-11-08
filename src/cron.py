# RUN THIS N AMOUNT OF TIMES
import os
import sys

# On Intel Macs, ctranslate2 (subtitles) and another native library each bundle
# an OpenMP runtime; loading both aborts with "OMP: Error #15". Allow it, before
# any of those libraries load.
if sys.platform == "darwin":
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

from status import *
from cache import get_accounts
from config import get_verbose
from classes.Tts import TTS
from classes.Twitter import Twitter
from classes.YouTube import YouTube
from config import get_script_queue
from llm_provider import select_model
from post_bridge_integration import maybe_crosspost_youtube_short
import script_queue

def main():
    """Main function to post content to Twitter or upload videos to YouTube.

    This function determines its operation based on command-line arguments:
    - If the purpose is "twitter", it initializes a Twitter account and posts a message.
    - If the purpose is "youtube", it initializes a YouTube account, generates a video with TTS, and uploads it.

    Command-line arguments:
        sys.argv[1]: A string indicating the purpose, either "twitter" or "youtube".
        sys.argv[2]: A string representing the account UUID.
        sys.argv[3]: The Ollama model name (needed when the LLM writes the script).
        --no-upload: Optional flag (YouTube only). Generate the video and stop,
            without uploading or marking a queued script as posted.

    The function also handles verbose output based on user settings and reports success or errors as appropriate.

    Args:
        None. The function uses command-line arguments accessed via sys.argv.

    Returns:
        None. The function performs operations based on the purpose and account UUID and does not return any value."""
    flags = {arg for arg in sys.argv[1:] if arg.startswith("--")}
    args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    purpose = str(args[0])
    account_id = str(args[1])
    model = str(args[2]) if len(args) > 2 else None
    no_upload = "--no-upload" in flags

    if model:
        select_model(model)

    verbose = get_verbose()

    if purpose == "twitter":
        if not model:
            error("No Ollama model specified. Pass model name as third argument.")
            sys.exit(1)
        accounts = get_accounts("twitter")

        if not account_id:
            error("Account UUID cannot be empty.")

        for acc in accounts:
            if acc["id"] == account_id:
                if verbose:
                    info("Initializing Twitter...")
                twitter = Twitter(
                    acc["id"],
                    acc["nickname"],
                    acc["firefox_profile"],
                    acc["topic"]
                )
                twitter.post()
                if verbose:
                    success("Done posting.")
                break
    elif purpose == "youtube":
        # Ready-made script from the queue, if enabled
        queued = None
        queue = get_script_queue()
        if queue["enabled"]:
            queued = script_queue.next_script()
            if queued is None:
                if queue["when_empty"] == "skip":
                    warning("Script queue is empty. Nothing to post; add scripts to the queue folder.")
                    return
                info("Script queue is empty. Letting the LLM write this one.")
            elif verbose:
                info(f"Using queued script: {queued[0]}")

        if queued is None and not model:
            error("No Ollama model specified. Pass model name as third argument.")
            sys.exit(1)

        tts = TTS()

        accounts = get_accounts("youtube")

        if not account_id:
            error("Account UUID cannot be empty.")

        for acc in accounts:
            if acc["id"] == account_id:
                if verbose:
                    info("Initializing YouTube...")
                youtube = YouTube(
                    acc["id"],
                    acc["nickname"],
                    acc["firefox_profile"],
                    acc["niche"],
                    acc["language"]
                )
                youtube.generate_video(tts, script_spec=queued[1] if queued else None)
                if no_upload:
                    youtube.browser.quit()
                    success(f"Generated (not uploaded): {youtube.video_path}")
                    break
                upload_success = youtube.upload_video()
                if upload_success:
                    if verbose:
                        success("Uploaded Short.")
                    if queued:
                        script_queue.mark_posted(queued[0], youtube.metadata.get("title", ""),
                                                 youtube.video_path)
                    maybe_crosspost_youtube_short(
                        video_path=youtube.video_path,
                        title=youtube.metadata.get("title", ""),
                        interactive=False,
                    )
                else:
                    warning("YouTube upload failed. Skipping Post Bridge cross-post.")
                break
        else:
            error(f"No YouTube account with ID {account_id}.")
            sys.exit(1)
    else:
        error("Invalid Purpose, exiting...")
        sys.exit(1)

if __name__ == "__main__":
    main()
