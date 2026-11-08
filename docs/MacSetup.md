# Automated YouTube Shorts on a Mac

This sets up a Mac to make and upload a Short on a schedule, using ready-made
scripts from `content/queue/`, 8-bit pixel-art visuals and generated chiptune
music. No AI image API key is needed.

Allow about 30–45 minutes the first time. Afterwards the Mac must be **on,
awake and logged in** at the scheduled times (the screen can be locked).

---

## 1. Install the tools

| Tool | How | Notes |
|---|---|---|
| Git | Open **Terminal** and run `xcode-select --install`, then click Install. | Skip if `git --version` already works. |
| Python **3.12** | Download the macOS installer from https://www.python.org/downloads/release/python-31210/ (any 3.12.x). | Python 3.13 will not work. After installing, open **Applications → Python 3.12** and double-click **Install Certificates.command**. Without this, downloads fail with SSL errors. |
| Firefox | https://www.mozilla.org/firefox/ | Used to upload to YouTube. |
| Ollama *(optional)* | https://ollama.com/download/mac | Only needed if you want the AI to write scripts when the queue runs out. Then run `ollama pull llama3.2:3b`. |

If you use Homebrew, `brew install python@3.12 git` and
`brew install --cask firefox` work too.

ImageMagick is **not** needed with the pixel-art style.

## 2. Download the project

In **Terminal**, run these one at a time:

```bash
cd ~
```

```bash
git clone -b wonderbytes-automation https://github.com/Docin4k/moneyprinterv2.git MoneyPrinterV2
```

```bash
cd ~/MoneyPrinterV2
```

```bash
python3.12 -m venv venv
```

```bash
source venv/bin/activate
```

Then install the packages. Check your Mac's chip first: Apple menu →
**About This Mac**. It says **Chip: Apple M1/M2/M3/M4** or **Processor: Intel**.

On an **Apple Silicon** Mac (M1–M4) with macOS 14 or newer:

```bash
pip install -r requirements.txt
```

On an **Intel** Mac, or any Mac on macOS 13 or older:

```bash
pip install -r requirements-mac-intel.txt
```

This downloads 1–3 GB and can take 10–20 minutes. If you see
`Building wheel for ...` sit there for minutes, press Control+C: that package
is being compiled because your Mac needs the other list.

Keep the project in your home folder (`~/MoneyPrinterV2`) as above. macOS
blocks scheduled jobs from reading `Documents`, `Desktop` and `Downloads`, so a
copy there would fail when it runs on its own.

## 3. Make a Firefox profile for the channel

1. Open Firefox and go to `about:profiles` in the address bar.
2. Click **Create a New Profile** → Continue → name it `wonderbytes` → **Done**.
3. Next to the new profile, click **Launch profile in new browser**.
4. In that window, sign in to YouTube with the Google account for the channel,
   and create the **WonderBytes** channel if you haven't yet
   (youtube.com → profile picture → **Create a channel**).
5. Go back to `about:profiles` and copy the **Root Directory** of the
   `wonderbytes` profile. It looks like
   `/Users/you/Library/Application Support/Firefox/Profiles/abcd1234.wonderbytes`.
6. **Quit that Firefox window.** Firefox can't open a profile that is already
   open, so leave the WonderBytes window closed whenever an upload is due.
   (Your normal Firefox window is fine.)

## 4. Configure

Run this from the project folder. It creates `config.json`, finds the
`wonderbytes` Firefox profile from step 3, and fills in every setting:

```bash
python scripts/mac/configure_wonderbytes.py
```

It prints the settings it wrote. If it can't find the profile, it says so;
you can also give the path yourself:

```bash
python scripts/mac/configure_wonderbytes.py --profile "/Users/you/Library/Application Support/Firefox/Profiles/abcd1234.wonderbytes"
```

It leaves `"headless": false` so you can watch the first upload. Once uploads
work, run it again with `--headless` to hide Firefox.

## 5. Create the account in the app

```bash
python src/main.py
```

Choose **1** (YouTube Shorts Automation) → `Yes` to create an account, then enter:

- nickname: `WonderBytes`
- Firefox profile path: the Root Directory from step 3
- niche: `surprising science and space facts`
- language: `English`

Then choose **5** (Quit).

## 6. Test

Show the account ID:

```bash
python -c "import json;[print(a['nickname'], a['id']) for a in json.load(open('.mp/youtube.json'))['accounts']]"
```

Make a video **without uploading** (replace `<id>` with the ID shown):

```bash
scripts/mac/run_youtube.sh <id> --no-upload
```

It takes a few minutes. The last lines of `logs/youtube.log` show where the MP4
was saved (inside `.mp/`). To watch it:

```bash
open .mp
```

Then do one **real upload** and watch Firefox do it:

```bash
scripts/mac/run_youtube.sh <id>
```

Check YouTube Studio. If it worked, `.mp/script_queue.json` lists the first
script as posted, and the next run uses the second one.

## 7. Schedule it

Once a day at 5 pm:

```bash
scripts/mac/schedule_youtube.sh --nickname WonderBytes --times 17:00
```

Twice a day:

```bash
scripts/mac/schedule_youtube.sh --nickname WonderBytes --times 12:00,18:00
```

Run the scheduled job right now to check it:

```bash
scripts/mac/schedule_youtube.sh --run-now
```

Watch what it's doing:

```bash
tail -f logs/youtube.log
```

Stop the schedule completely:

```bash
scripts/mac/schedule_youtube.sh --remove
```

Running the schedule command again with different times replaces the old
schedule.

## Keeping it running

- **Sleep:** if the Mac is asleep at a scheduled time, the job runs as soon as
  it wakes. If it's shut down, that day's run is skipped. To keep it awake while
  plugged in, go to **System Settings → Battery → Options** (or **Energy** on a
  desktop Mac) and turn on **Prevent automatic sleeping when the display is
  off**. To wake it a few minutes before a 5 pm upload, you can run
  `sudo pmset repeat wakeorpoweron MTWRFSU 16:55:00`.
- **Logged in:** the job needs you logged in (a locked screen is fine).
- **Firefox:** keep the `wonderbytes` profile signed in to YouTube, and its
  window closed at upload time.
- **More scripts:** add JSON files to `content/queue/` (see `content/README.md`).
  With `"when_empty": "skip"`, nothing is posted once the queue runs out.
- **Logs:** each run is in `logs/youtube.log`; launchd's own messages are in
  `logs/launchd.log`.

## Troubleshooting

| Problem | Fix |
|---|---|
| Install stuck on `Building wheel for opencv-python-headless` (or torch, onnxruntime) | Press Control+C and use `pip install -r requirements-mac-intel.txt` (see step 2). |
| `python3.12: command not found` | Install Python 3.12 from python.org (step 1), then open a new Terminal window. |
| `SSL: CERTIFICATE_VERIFY_FAILED` | Run **Applications → Python 3.12 → Install Certificates.command**. |
| `config.json has a mistake` | Run `cp config.example.json config.json`, then `python scripts/mac/configure_wonderbytes.py` again. |
| `Firefox profile path does not exist` | Check the path in the account (step 5) and in `config.json`. |
| Firefox says the profile is already in use | Quit the WonderBytes Firefox window, then run again. |
| `Operation not permitted` in `logs/launchd.log` | The project is in Documents, Desktop or Downloads. Move it to `~/MoneyPrinterV2` and run the schedule command again. |
| Upload fails or stops partway | Run with `"headless": false` and watch. YouTube sometimes changes its upload page, and the app's selectors may need updating. Make sure the profile is still signed in. |
| Nothing happens at the scheduled time | Check `logs/launchd.log` and `logs/youtube.log`, and that the Mac was awake and you were logged in. `launchctl print gui/$(id -u)/com.moneyprinterv2.youtube` shows the job's state. |
| `OMP: Error #15` and `Abort trap: 6` in the log | Two libraries load their own OpenMP runtime on Intel Macs. Run `git pull` to get the fix (it sets `KMP_DUPLICATE_LIB_OK=TRUE` on macOS). |
| `Script queue is empty` in the log | Add more scripts to `content/queue/`. |
