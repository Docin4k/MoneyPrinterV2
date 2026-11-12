# Handoff: the WonderBytes automation, and starting another channel

Everything a new Claude session (or a person) needs to understand this setup
and launch another automated YouTube Shorts channel with it.

## Starting a new Claude session

1. Open Claude Code on the web and start a **new session with the repository
   `Docin4k/moneyprinterv2` selected**.
2. Paste this as the first message, filling in the brackets:

> Read docs/HANDOFF.md, docs/MacSetup.md, content/README.md and
> content/WRITING_GUIDE.md in this repo, on branch wonderbytes-automation.
> I run the WonderBytes channel with this automation on my Intel Mac
> (macOS 11). I want to start a second channel called [NAME] about [NICHE],
> following "Adding another channel" in HANDOFF.md. Work on a new branch
> channel-[name] made from wonderbytes-automation, and don't change
> WonderBytes' branch or queue.

## How the system works

**Daily, on the Mac** (`scripts/mac/run_youtube.sh`, started by launchd from
`scripts/mac/schedule_youtube.sh`):

1. `git pull --ff-only` picks up new scripts from GitHub.
2. `src/cron.py youtube <account id>` takes the next unposted script from
   `content/queue/` (filename order; posted ones are listed in
   `.mp/script_queue.json`).
3. `YouTube.generate_video` (`src/classes/YouTube.py`) builds the Short:
   - **No voice-over** (`"voiceover": false`): each sentence stays on screen
     for its reading time; captions come straight from the script.
   - **8-bit visuals** (`"visual_style": "pixel_art"`, `src/pixel_art.py`):
     one animated scene per sentence, drawn at 360x640 and scaled 3x to
     1080x1920.
   - **Music** (`"music_source": "chiptune"`, `src/chiptune.py`): an original
     track per video in one of 8 styles; the script's `music_style` picks it.
4. `upload_video` drives YouTube Studio in Firefox with Selenium, using a
   Firefox profile that's already signed in to the channel, then marks the
   script as posted.

**Weekly, in the cloud:** a Claude scheduled task ("WonderBytes weekly
scripts", Sundays 6:35 pm Mountain) writes 14 new scripts following
`content/WRITING_GUIDE.md`, adds them with `scripts/queue_tools.py add`, and
pushes to `wonderbytes-automation`. It runs in the original Claude session.

## Important files

| File | Purpose |
|---|---|
| `config.json` | Settings on each machine (not in git). Made by `scripts/mac/configure_wonderbytes.py`. |
| `content/channel.json` | Channel name, niche, call to action, tagline. |
| `content/queue/*.json` | The scripts; format in `content/README.md`. |
| `content/WRITING_GUIDE.md` | Rules for writing scripts (accuracy first). |
| `scripts/queue_tools.py` | `check`, `topics`, `add batch.json`. |
| `scripts/mac/run_youtube.sh` | One run: pull, make and upload, log to `logs/youtube.log`. |
| `scripts/mac/schedule_youtube.sh` | Daily launchd schedule per channel (`--times`, `--run-now`, `--remove`). |
| `scripts/mac/diagnose.py` | Checks each native library separately. |
| `scripts/make_channel_art.py` | Profile picture and banner in the same style. |
| `docs/MacSetup.md`, `docs/WindowsSetup.md` | Machine setup. |

## Lessons from the Intel Mac (macOS 11.7, x86_64)

- **Python 3.12 only.** KittenTTS's dependency `misaki` doesn't support 3.13.
  On python.org's Python, run "Install Certificates.command".
- **Install with `requirements-mac-intel.txt`.** Current torch, onnxruntime
  and OpenCV have no Intel/macOS 11 builds; it pins versions that do. torch
  and OpenCV are never loaded when making videos.
- **OpenMP clash.** ctranslate2 and other native libraries each bundle OpenMP.
  `main.py` and `cron.py` set `KMP_DUPLICATE_LIB_OK=TRUE`, plus
  `OMP_NUM_THREADS=1` on Intel Macs. With the voice-over off, KittenTTS and
  Whisper aren't loaded at all, which avoids this entirely.
- **Keep the project in the home folder.** macOS blocks launchd jobs from
  Documents, Desktop and Downloads.
- **Firefox profile:** it must be signed in to the channel, and its window
  must be closed at upload time. A profile already in use makes Firefox exit
  immediately. The profile name match is case-insensitive.
- **YouTube Studio changes over time.** Studio's Trusted Types CSP breaks
  Selenium's `clear()` (text is replaced with select-all and delete), the
  hashtag popup can cover the description (handled by focusing directly),
  and pages load slowly (every step waits up to 1–2 minutes). On failure,
  the log names the step and `logs/upload-failure.png` shows the page.
- **YouTube visibility** is chosen by name: `youtube_visibility`, default
  `public`.

## Adding another channel

A second channel gets **its own branch, folder, queue, Firefox profile and
schedule**, so it never touches WonderBytes.

### On GitHub (done by the new Claude session)

1. Make branch `channel-<name>` from `wonderbytes-automation`.
2. Edit `content/channel.json`: name, niche, call to action, tagline.
3. Empty `content/queue/` and rewrite `content/WRITING_GUIDE.md` for the new
   niche (keep the accuracy rules and batch format).
4. Write the first batch of scripts and add them with
   `python scripts/queue_tools.py add batch.json`.
5. **Visuals:** the scenes in `src/pixel_art.py` are space-themed. For a
   non-space niche, add scenes for it (follow the existing scene functions:
   design units are 180x320, use `XX`/`YY` for shapes and `put`/`_plot` for
   points) and register them in `SCENES`.
6. Optionally create a weekly writing task for the new branch, like the
   WonderBytes one.

### On the Mac

1. Create the YouTube channel. Then in Firefox go to `about:profiles`, create
   a profile with the channel's name, sign in to the channel in it, and quit.
2. Clone the new branch into its **own folder**:
   ```bash
   git clone -b channel-<name> https://github.com/Docin4k/moneyprinterv2.git ~/<Name>Shorts
   ```
3. In that folder: `python3.12 -m venv venv`, `source venv/bin/activate`,
   `pip install -r requirements-mac-intel.txt`.
4. `python scripts/mac/configure_wonderbytes.py --profile-name <ProfileName>`.
   Then edit `subtitle_replacements` in `config.json` if speech-to-text could
   misspell the name; it's only used with a voice-over.
5. `python src/main.py` → YouTube → create the account with the new nickname.
6. Test with `scripts/mac/run_youtube.sh <id> --no-upload`, then do one real
   upload.
7. Schedule at **different times** from WonderBytes, so the Mac makes one
   video at a time:
   ```bash
   scripts/mac/schedule_youtube.sh --nickname <Nickname> --times 15:00,21:00
   ```
8. Channel art: `python scripts/make_channel_art.py --name <Name> --tagline "<tagline>"`.
