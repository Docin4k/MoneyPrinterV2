# Automated YouTube Shorts on Windows

This sets up a Windows PC to make and upload a Short on a schedule, using
ready-made scripts from `content/queue/`, 8-bit pixel-art visuals and
generated chiptune music. No AI image API key is needed.

You need about 30–45 minutes the first time. Afterwards the PC must be **on and
logged in** at the scheduled times (it can be locked).

---

## 1. Install the tools

Install these with their default options:

| Tool | Where | Notes |
|---|---|---|
| Python **3.12** | https://www.python.org/downloads/windows/ | On the first installer screen, tick **"Add python.exe to PATH"**. Python 3.13 will not work. |
| Git | https://git-scm.com/download/win | |
| Firefox | https://www.mozilla.org/firefox/ | Used to upload to YouTube. |
| Ollama *(optional)* | https://ollama.com/download/windows | Only needed if you want the AI to write scripts when the queue runs out. Then run `ollama pull llama3.2:3b` in a terminal. |

ImageMagick is **not** needed with the pixel-art style.

## 2. Download the project

Open **PowerShell** (Start menu → type "PowerShell") and run these one at a time:

```powershell
cd $HOME\Documents
git clone -b wonderbytes-automation https://github.com/Docin4k/moneyprinterv2.git MoneyPrinterV2
cd MoneyPrinterV2
py -3.12 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

The last step downloads a few GB and can take 10–20 minutes.

If `venv\Scripts\activate` says running scripts is disabled, run
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, answer `Y`, and try again.

## 3. Make a Firefox profile for the channel

1. Open Firefox and go to `about:profiles` in the address bar.
2. Click **Create a New Profile** → Next → name it `wonderbytes` → **Finish**.
3. Next to the new profile, click **Launch profile in new browser**.
4. In that window, sign in to YouTube with the Google account for the channel,
   and create the **WonderBytes** channel if you haven't yet
   (youtube.com → profile picture → **Create a channel**).
5. Go back to `about:profiles` and copy the **Root Directory** of the
   `wonderbytes` profile. It looks like
   `C:\Users\you\AppData\Roaming\Mozilla\Firefox\Profiles\abcd1234.wonderbytes`.
6. Close that Firefox window.

## 4. Configure

```powershell
copy config.example.json config.json
notepad config.json
```

Change these values (leave the rest as they are). In JSON, every `\` in a path
must be written as `\\`:

```json
"firefox_profile": "C:\\Users\\you\\AppData\\Roaming\\Mozilla\\Firefox\\Profiles\\abcd1234.wonderbytes",
"headless": false,
"ollama_model": "llama3.2:3b",
"tts_voice": "Bella",
"visual_style": "pixel_art",
"music_source": "chiptune",
"music_volume": 0.15,
"subtitle_replacements": {"wonder\\s*bites": "WonderBytes"},
"script_queue": {"enabled": true, "dir": "content/queue", "when_empty": "skip"},
```

Keep `"headless": false` until the first real upload has worked, so you can
watch it. Set it to `true` afterwards.

## 5. Create the account in the app

```powershell
python src\main.py
```

Choose **1** (YouTube Shorts Automation) → `Yes` to create an account, then enter:

- nickname: `WonderBytes`
- Firefox profile path: the Root Directory from step 3 (normal single `\`)
- niche: `surprising science and space facts`
- language: `English`

Then choose **5** (Quit) and close the window.

## 6. Test

Show the account ID:

```powershell
(Get-Content .mp\youtube.json | ConvertFrom-Json).accounts | Select-Object nickname, id
```

Make a video **without uploading** (replace `<id>` with the ID shown):

```powershell
scripts\windows\run_youtube.bat <id> --no-upload
```

It takes a few minutes. Check `logs\youtube.log`; the last lines show where the
MP4 was saved (inside `.mp\`). Watch it.

Then do one **real upload** and watch Firefox do it:

```powershell
scripts\windows\run_youtube.bat <id>
```

Check YouTube Studio. If it worked, `.mp\script_queue.json` now lists the first
script as posted, and the next run will use the second one.

## 7. Schedule it

Once a day at 5 pm:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\windows\schedule_youtube.ps1 -Nickname WonderBytes -Times 17:00
```

Twice a day:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\windows\schedule_youtube.ps1 -Nickname WonderBytes -Times 12:00,18:00
```

Run the task right now to check it:

```powershell
Start-ScheduledTask -TaskName "MoneyPrinterV2 YouTube Shorts"
```

You can see and edit it in **Task Scheduler** (Start menu → "Task Scheduler" →
Task Scheduler Library). To stop it completely:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\windows\schedule_youtube.ps1 -Remove
```

## Keeping it running

- **Power:** Settings → System → Power → set **Sleep** to *Never* while plugged
  in, or the PC must be awake at the scheduled times. A run missed while the PC
  was off happens as soon as you're back.
- **Logged in:** the task needs you logged in (locking the screen is fine),
  because it uses your Firefox profile.
- **More scripts:** add JSON files to `content\queue\` (see `content\README.md`).
  With `"when_empty": "skip"`, nothing is posted once the queue runs out.
- **Logs:** everything goes to `logs\youtube.log`.

## Troubleshooting

| Problem | Fix |
|---|---|
| `py -3.12` not found | Reinstall Python 3.12 and tick "Add python.exe to PATH". |
| Upload fails or stops partway | Run with `"headless": false` and watch. YouTube sometimes changes its upload page, and the app's selectors may need updating. Make sure the profile is still signed in. |
| `Firefox profile path does not exist` | Check the path in the account (step 5) and in `config.json`. |
| Nothing happens at the scheduled time | Check Task Scheduler → the task → **History**, and `logs\youtube.log`. Make sure you were logged in and the PC was awake. |
| `Script queue is empty` in the log | Add more scripts to `content\queue\`. |
