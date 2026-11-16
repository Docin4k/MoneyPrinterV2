# Setting up DinoBytes on the Mac

DinoBytes is the third channel: dinosaurs and prehistoric life, 8-bit
prehistoric scenes, chiptune music, no voice-over. It runs from **its own folder** with
**its own Firefox profile and schedule**, so WonderBytes and DinoBytes are never touched.

Its code lives on the branch `channel-dinobytes`. It posts the scripts in
`content/queue/` (28 to start); a weekly Claude task adds 14 more each week.

## 1. Create the YouTube channel

1. Go to youtube.com, signed in with your Google account.
2. Click your profile picture → **Settings** → **Add or manage your
   channel(s)** → **Create a channel**. Name it **DinoBytes**.
3. Upload the profile picture and banner (step 7 makes them).

## 2. Make a Firefox profile for it

1. **Quit Firefox completely** (Firefox menu → Quit Firefox).
2. Open Firefox, type `about:profiles` in the address bar, press Return.
3. Click **Create a New Profile** → Continue → name it **DinoBytes** → Finish.
4. Next to the DinoBytes profile, click **Launch profile in new browser**.
5. In that new window, sign in to YouTube and **switch to the DinoBytes
   channel** (profile picture → Switch account → DinoBytes).
6. Go to studio.youtube.com once to make sure it opens DinoBytes.
7. Quit Firefox. (Your normal profile stays your default.)

## 3. Download the channel's copy of the project

Open Terminal and run:

```bash
git clone -b channel-dinobytes https://github.com/Docin4k/moneyprinterv2.git ~/DinoBytes
```

```bash
cd ~/DinoBytes
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
python scripts/mac/configure_wonderbytes.py --profile-name DinoBytes
```

(The script is shared by both channels; it finds the DinoBytes Firefox
profile and turns on the queue, pixel art, chiptune and no voice-over.)

Then create the account:

```bash
python src/main.py
```

Choose **YouTube Shorts Automation** → create a new account → nickname
**DinoBytes** (one word), niche "dinosaur facts", language English. Then quit
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
python scripts/make_channel_art.py --theme dino --name "DinoBytes" --tagline "Prehistoric facts, pixel by pixel"
```

The pictures are in the `channel-art` folder: `profile.png` (or
`profile-letters.png`) and `banner.png`. Upload them in YouTube Studio →
Customization → Branding.

## 8. Schedule it

At different times from WonderBytes (12:00, 18:00) and Pixel Abyss (15:00,
21:00), so the Mac makes one video at a time:

```bash
scripts/mac/schedule_youtube.sh --nickname DinoBytes --times 13:30,19:30
```

Check both channels are scheduled:

```bash
launchctl list | grep moneyprinterv2
```

You should see `com.moneyprinterv2.youtube` (WonderBytes),
`com.moneyprinterv2.youtube.pixelabyss` and `com.moneyprinterv2.youtube.dinobytes`.

## 9. Phone notifications and the channel lock

Use the same ntfy topic as the other channels, so all three report to the
same place:

```bash
cd ~/DinoBytes && venv/bin/python -c "import json; c=json.load(open('config.json')); c['ntfy_topic']='YOUR-NTFY-TOPIC'; json.dump(c, open('config.json','w'), indent=2)"
```

```bash
venv/bin/python scripts/notify.py --test
```

Then lock the folder to the DinoBytes channel, so a profile switched to
another channel can never post here. Get the ID from
`studio.youtube.com/channel/UC...` in the DinoBytes Firefox profile:

```bash
venv/bin/python -c "import json; c=json.load(open('config.json')); c['youtube_channel_id']='UC...'; json.dump(c, open('config.json','w'), indent=2)"
```

## If something goes wrong

Each channel has its own log:

```bash
tail -30 ~/DinoBytes/logs/youtube.log
```

Remember: the Mac must be awake at upload time, and **all Firefox windows must
be closed**, because a profile that is already open makes Firefox exit.
