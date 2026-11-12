# Setting up Pixel Abyss on the Mac

Pixel Abyss is the second channel: strange deep sea facts, 8-bit underwater
scenes, chiptune music, no voice-over. It runs from **its own folder** with
**its own Firefox profile and schedule**, so WonderBytes is never touched.

Its code lives on the branch `channel-pixelabyss`. It posts the scripts in
`content/queue/` (28 to start); a weekly Claude task adds 14 more each week.

## 1. Create the YouTube channel

1. Go to youtube.com, signed in with your Google account.
2. Click your profile picture → **Settings** → **Add or manage your
   channel(s)** → **Create a channel**. Name it **Pixel Abyss**.
3. Upload the profile picture and banner (step 7 makes them).

## 2. Make a Firefox profile for it

1. **Quit Firefox completely** (Firefox menu → Quit Firefox).
2. Open Firefox, type `about:profiles` in the address bar, press Return.
3. Click **Create a New Profile** → Continue → name it **PixelAbyss** → Finish.
4. Next to the PixelAbyss profile, click **Launch profile in new browser**.
5. In that new window, sign in to YouTube and **switch to the Pixel Abyss
   channel** (profile picture → Switch account → Pixel Abyss).
6. Go to studio.youtube.com once to make sure it opens Pixel Abyss.
7. Quit Firefox. (Your normal profile stays your default.)

## 3. Download the channel's copy of the project

Open Terminal and run:

```bash
git clone -b channel-pixelabyss https://github.com/Docin4k/moneyprinterv2.git ~/PixelAbyss
```

```bash
cd ~/PixelAbyss
```

## 4. Install

```bash
python3.12 -m venv venv
```

```bash
source venv/bin/activate
```

```bash
pip install -r requirements-mac-intel.txt
```

This takes a few minutes, like it did for WonderBytes.

## 5. Configure

```bash
python scripts/mac/configure_wonderbytes.py --profile-name PixelAbyss
```

(The script is shared by both channels; it finds the PixelAbyss Firefox
profile and turns on the queue, pixel art, chiptune and no voice-over.)

Then create the account:

```bash
python src/main.py
```

Choose **YouTube Shorts Automation** → create a new account → nickname
**PixelAbyss** (one word), niche "deep sea facts", language English. Then quit
with the menu's exit option.

## 6. Test, then upload one

Find the account id:

```bash
python -c "import json; print([(a['nickname'], a['id']) for a in json.load(open('.mp/youtube.json'))['accounts']])"
```

Make a test video without uploading (put your id in place of YOUR-ID):

```bash
scripts/mac/run_youtube.sh YOUR-ID --no-upload
```

The finished video is in `.mp/`. When it looks right, do a real upload:

```bash
scripts/mac/run_youtube.sh YOUR-ID
```

## 7. Channel art

```bash
python scripts/make_channel_art.py --theme ocean --name "Pixel Abyss" --tagline "Weird true facts from the deep"
```

The pictures are in the `channel-art` folder: `profile.png` (or
`profile-letters.png`) and `banner.png`. Upload them in YouTube Studio →
Customization → Branding.

## 8. Schedule it

At different times from WonderBytes (12:00 and 18:00), so the Mac makes one
video at a time:

```bash
scripts/mac/schedule_youtube.sh --nickname PixelAbyss --times 15:00,21:00
```

Check both channels are scheduled:

```bash
launchctl list | grep moneyprinterv2
```

You should see `com.moneyprinterv2.youtube` (WonderBytes) and
`com.moneyprinterv2.youtube.pixelabyss`.

## If something goes wrong

Each channel has its own log:

```bash
tail -30 ~/PixelAbyss/logs/youtube.log
```

Remember: the Mac must be awake at upload time, and **all Firefox windows must
be closed**, because a profile that is already open makes Firefox exit.
