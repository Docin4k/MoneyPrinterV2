"""Original chiptune background music, generated from a seed.

Each seed picks one of several styles (adventure, chill, space ambient,
march, waltz, funk, boss battle, music box, and the mysterious ocean styles
in OCEAN_STYLES) and then a key, tempo, scale,
chord progressions, instruments, bass and drum patterns and a melody. Tracks
have an intro, A and B sections with different progressions, and sometimes a
key change, so consecutive videos sound clearly different.

Voices use 8-bit style waveforms: pulse waves (several duty cycles), a
triangle wave, a stepped "8-bit saw", and noise for drums. Some styles add
an echo or swing.

Usage:
    from chiptune import generate_track, describe
    generate_track("music.wav", duration=45, seed=1234)
    describe(1234)  # e.g. "chill, D dorian, 88 BPM"
"""
import random
import wave
import zlib

import numpy as np

SR = 44100
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

MODES = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "lydian": [0, 2, 4, 6, 7, 9, 11],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "harmonic minor": [0, 2, 3, 5, 7, 8, 11],
    "melodic minor": [0, 2, 3, 5, 7, 9, 11],
    "lydian dominant": [0, 2, 4, 6, 7, 9, 10],
}
MAJORISH = {"major", "mixolydian", "lydian", "lydian dominant"}

# Chord roots as scale degrees (0 = tonic), one chord per bar
PROGRESSIONS = {
    "majorish": [[0, 4, 5, 3], [0, 5, 3, 4], [5, 3, 0, 4], [0, 3, 5, 4], [0, 3, 0, 4], [3, 4, 2, 5],
                 [0, 2, 3, 4], [0, 6, 3, 4], [5, 4, 3, 4], [0, 3, 1, 4]],
    "minorish": [[0, 5, 2, 6], [0, 3, 5, 4], [0, 6, 5, 6], [0, 5, 3, 4], [0, 3, 6, 2], [5, 6, 0, 0],
                 [0, 6, 5, 4], [3, 4, 0, 0], [0, 1, 0, 6], [0, 4, 5, 6]],
    # Floating, unresolved progressions for the mysterious ocean styles: the
    # lydian I-II and the dorian i-IV sway, with no dark minor cadences
    "mystic_major": [[0, 1, 0, 1], [0, 1, 4, 0], [0, 5, 1, 0], [0, 2, 1, 0], [0, 1, 5, 4], [0, 4, 1, 1]],
    "mystic_minor": [[0, 3, 0, 3], [0, 6, 3, 0], [0, 1, 6, 0], [0, 3, 6, 3], [0, 4, 3, 6], [0, 2, 3, 0]],
}

# Drum patterns: lists of step indexes within a bar (16 steps, or 12 in 3/4)
DRUMS = {
    "rock": {"kick": [0, 8, 10], "snare": [4, 12], "hat": list(range(0, 16, 2))},
    "soft": {"kick": [0], "snare": [8], "hat": [0, 4, 8, 12]},
    "march": {"kick": [0, 8], "snare": [4, 12, 14, 15], "hat": []},
    "funk": {"kick": [0, 3, 10], "snare": [4, 12], "ghost": [7, 15], "hat": list(range(16)), "open": [14]},
    "driving": {"kick": [0, 4, 8, 12], "snare": [4, 12], "hat": list(range(16))},
    "waltz": {"kick": [0], "snare": [4, 8], "hat": [2, 6, 10]},
}

# Melody rhythms: (start step, length in steps) for one bar
RHYTHMS = {
    "even": [[(0, 4), (4, 2), (6, 2), (8, 4), (12, 4)], [(0, 2), (2, 2), (4, 4), (10, 2), (12, 4)],
             [(0, 6), (6, 2), (8, 2), (10, 2), (12, 4)], [(0, 3), (3, 3), (6, 2), (8, 8)]],
    "long": [[(0, 8), (8, 8)], [(0, 12), (12, 4)], [(0, 4), (4, 12)], [(0, 6), (8, 8)]],
    "busy": [[(i, 1) for i in range(0, 16)], [(0, 2), (2, 1), (3, 1), (4, 2), (6, 2), (8, 1), (9, 1), (10, 2), (12, 4)],
             [(0, 1), (1, 1), (2, 2), (4, 1), (5, 1), (6, 2), (8, 2), (10, 2), (12, 2), (14, 2)]],
    "syncopated": [[(0, 3), (3, 3), (6, 4), (10, 2), (12, 4)], [(2, 2), (4, 1), (6, 3), (10, 3), (14, 2)],
                   [(0, 1), (3, 3), (7, 2), (9, 3), (13, 3)]],
    "dotted": [[(0, 3), (3, 1), (4, 3), (7, 1), (8, 4), (12, 4)], [(0, 3), (3, 1), (4, 4), (8, 3), (11, 1), (12, 4)]],
    "waltz": [[(0, 4), (4, 4), (8, 4)], [(0, 6), (6, 2), (8, 4)], [(0, 2), (2, 2), (4, 4), (8, 4)], [(0, 8), (8, 4)]],
}

STYLES = {
    "adventure": dict(bpm=(118, 140), modes=["major", "mixolydian"], meter=4, lead=("pulse", 0.25),
                      arp=("pulse", 0.125), arp_rate=1, bass="octave", drums="rock", rhythm="even",
                      echo=0.0, swing=0.0, key_change=0.5),
    "chill": dict(bpm=(76, 94), modes=["major", "dorian", "lydian"], meter=4, lead=("triangle", None),
                  arp=("pulse", 0.25), arp_rate=2, bass="long", drums="soft", rhythm="long",
                  echo=0.35, swing=0.14, key_change=0.0),
    "space ambient": dict(bpm=(66, 84), modes=["lydian", "minor", "dorian"], meter=4, lead=("pulse", 0.5),
                          arp=("pulse", 0.125), arp_rate=1, bass="drone", drums=None, rhythm="long",
                          echo=0.5, swing=0.0, key_change=0.0),
    "march": dict(bpm=(104, 122), modes=["major", "minor"], meter=4, lead=("pulse", 0.25),
                  arp=None, arp_rate=4, bass="alternating", drums="march", rhythm="dotted",
                  echo=0.0, swing=0.0, key_change=0.4),
    "waltz": dict(bpm=(126, 156), modes=["major", "minor", "harmonic minor"], meter=3, lead=("pulse", 0.5),
                  arp=("pulse", 0.25), arp_rate=4, bass="waltz", drums="waltz", rhythm="waltz",
                  echo=0.2, swing=0.0, key_change=0.2),
    "funk": dict(bpm=(94, 112), modes=["dorian", "mixolydian"], meter=4, lead=("saw", None),
                 arp=("pulse", 0.125), arp_rate=2, bass="syncopated", drums="funk", rhythm="syncopated",
                 echo=0.0, swing=0.12, key_change=0.0),
    "boss battle": dict(bpm=(140, 168), modes=["minor", "phrygian", "harmonic minor"], meter=4,
                        lead=("pulse", 0.25), arp=("pulse", 0.125), arp_rate=1, bass="driving",
                        drums="driving", rhythm="busy", echo=0.0, swing=0.0, key_change=0.6),
    "music box": dict(bpm=(84, 104), modes=["major", "lydian"], meter=3, lead=("triangle", None),
                      arp=("triangle", None), arp_rate=2, bass="soft", drums=None, rhythm="waltz",
                      echo=0.3, swing=0.0, key_change=0.0, octave=1),
    # ---- Ocean styles (Pixel Abyss): mysterious and curious, never scary.
    # Extra options: mystic (floating progressions), pad (soft held chords),
    # ping (a sonar ping every other bar), bubbles (chance per step of a
    # rising bubble blip).
    "deep current": dict(bpm=(62, 74), modes=["dorian", "melodic minor"], meter=4, lead=("triangle", None),
                         arp=("pulse", 0.125), arp_rate=4, bass="drone", drums=None, rhythm="long",
                         echo=0.5, swing=0.0, key_change=0.0, mystic=True, pad=True, bubbles=0.03),
    "sonar": dict(bpm=(70, 84), modes=["lydian", "dorian"], meter=4, lead=("pulse", 0.5),
                  arp=("triangle", None), arp_rate=2, bass="long", drums=None, rhythm="long",
                  echo=0.45, swing=0.0, key_change=0.0, mystic=True, pad=True, ping=True),
    "bioluminescence": dict(bpm=(84, 100), modes=["lydian", "lydian dominant"], meter=4, lead=("triangle", None),
                            arp=("pulse", 0.125), arp_rate=1, bass="soft", drums=None, rhythm="even",
                            echo=0.4, swing=0.0, key_change=0.0, octave=1, mystic=True, bubbles=0.02),
    "tide pool": dict(bpm=(86, 98), modes=["dorian", "mixolydian"], meter=4, lead=("pulse", 0.25),
                      arp=("pulse", 0.25), arp_rate=2, bass="long", drums="soft", rhythm="syncopated",
                      echo=0.25, swing=0.12, key_change=0.0, mystic=True, bubbles=0.05),
    "kelp drift": dict(bpm=(96, 114), modes=["dorian", "melodic minor"], meter=3, lead=("triangle", None),
                       arp=("triangle", None), arp_rate=2, bass="waltz", drums=None, rhythm="waltz",
                       echo=0.35, swing=0.0, key_change=0.0, mystic=True, pad=True),
    "explorer": dict(bpm=(96, 112), modes=["lydian dominant", "mixolydian", "dorian"], meter=4,
                     lead=("pulse", 0.25), arp=("pulse", 0.125), arp_rate=1, bass="octave", drums="soft",
                     rhythm="dotted", echo=0.2, swing=0.0, key_change=0.3, mystic=True, ping=True),
    "midnight zone": dict(bpm=(54, 64), modes=["dorian", "lydian"], meter=4, lead=("pulse", 0.5),
                          arp=None, arp_rate=4, bass="drone", drums=None, rhythm="long",
                          echo=0.6, swing=0.0, key_change=0.0, mystic=True, pad=True, ping=True, bubbles=0.02),
    "sunken treasure": dict(bpm=(90, 108), modes=["melodic minor", "dorian"], meter=3, lead=("triangle", None),
                            arp=("triangle", None), arp_rate=2, bass="soft", drums=None, rhythm="waltz",
                            echo=0.3, swing=0.0, key_change=0.0, octave=1, mystic=True, bubbles=0.03),
}
OCEAN_STYLES = ["deep current", "sonar", "bioluminescence", "tide pool", "kelp drift", "explorer",
                "midnight zone", "sunken treasure"]


def seed_from_text(text: str) -> int:
    return zlib.crc32(text.encode("utf-8"))


def _plan(seed: int, style: str | None = None) -> dict:
    """Every random musical choice for a seed, made in a fixed order.
    `style` forces one of STYLES; otherwise the seed picks it."""
    rng = random.Random(seed)
    style_name = rng.choice(list(STYLES))
    if style in STYLES:
        style_name = style
    style = STYLES[style_name]
    mode = rng.choice(style["modes"])
    family = "majorish" if mode in MAJORISH else "minorish"
    if style.get("mystic"):
        family = "mystic_" + ("major" if mode in MAJORISH else "minor")
    prog_a = rng.choice(PROGRESSIONS[family])
    prog_b = rng.choice([p for p in PROGRESSIONS[family] if p != prog_a])
    return {
        "rng": rng,
        "style_name": style_name,
        "style": style,
        "mode": mode,
        "root": rng.randint(55, 64),
        "bpm": rng.randint(*style["bpm"]),
        "prog_a": prog_a,
        "prog_b": prog_b,
        "arp_shape": rng.choice([[0, 1, 2, 1], [0, 1, 2, 3], [0, 2, 1, 2], [2, 1, 0, 1], [0, 2, 3, 2], [3, 2, 1, 0]]),
        "lead_duty": rng.choice([0.125, 0.25, 0.5]) if style["lead"][1] is not None else None,
        "key_change": rng.random() < style["key_change"],
        "intro_bars": rng.choice([1, 2]),
    }


def describe(seed: int, style: str | None = None) -> str:
    """Human-readable summary of the track a seed produces."""
    p = _plan(seed, style)
    return f"{p['style_name']}, {NOTE_NAMES[p['root'] % 12]} {p['mode']}, {p['bpm']} BPM"


# ------------------------------------------------------------- voices ----
def _freq(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def _phase(freq, n, glide_from=None, vibrato=0.0):
    t = np.arange(n) / SR
    f = np.full(n, freq, dtype=float)
    if glide_from:
        g = min(n, int(0.04 * SR))
        f[:g] = np.linspace(glide_from, freq, g)
    if vibrato:
        f *= 1 + vibrato * np.sin(2 * np.pi * 5.5 * t) * np.minimum(1, t / 0.2)
    return np.cumsum(f / SR) % 1.0


def _wave(kind, phase, duty=0.5, duty_sweep=False):
    if kind == "triangle":
        return 4 * np.abs(phase - 0.5) - 1
    if kind == "saw":
        return np.round((phase * 2 - 1) * 8) / 8  # stepped, like 4-bit hardware
    if duty_sweep:
        d = duty + 0.12 * np.sin(np.linspace(0, np.pi, len(phase)))
        return np.where(phase < d, 1.0, -1.0)
    return np.where(phase < duty, 1.0, -1.0)


def _env(n, attack=0.004, decay=0.25, sustain=0.6, release=0.03):
    t = np.arange(n) / SR
    env = np.minimum(1.0, t / attack) * (sustain + (1 - sustain) * np.exp(-t / decay))
    rel = int(release * SR)
    if rel and n > rel:
        env[-rel:] *= np.linspace(1, 0, rel)
    return env


def _add(buf, start, sig):
    end = min(len(buf), start + len(sig))
    if 0 <= start < end:
        buf[start:end] += sig[:end - start]


def _echo(sig, delay_s, feedback):
    out = sig.copy()
    d = int(delay_s * SR)
    tap = sig
    for _ in range(3):
        tap = np.concatenate([np.zeros(d), tap[:-d]]) * feedback
        out += tap
    return out


# -------------------------------------------------------------- track ----
def generate_track(path: str, duration: float, seed: int, volume: float = 0.8,
                   style: str | None = None) -> str:
    """Write a WAV file of at least `duration` seconds and return its path.
    `style` (one of STYLES) overrides the style the seed would pick."""
    p = _plan(seed, style)
    rng, style = p["rng"], p["style"]
    scale = MODES[p["mode"]]
    steps = 12 if style["meter"] == 3 else 16
    step = 60.0 / p["bpm"] / 4
    lead_kind, _ = style["lead"]
    octave_shift = style.get("octave", 0)

    def degree(d, octave=0, root=None):
        r = p["root"] if root is None else root
        return r + scale[d % 7] + 12 * (d // 7 + octave)

    def chord(d, root):
        return [degree(d, 0, root), degree(d + 2, 0, root), degree(d + 4, 0, root), degree(d + 7, 0, root)]

    def make_phrase(prog):
        bars = []
        for bar in range(4):
            rhythm = rng.choice(RHYTHMS[style["rhythm"]])
            rhythm = [(s, l) for s, l in rhythm if s < steps]
            notes, d = [], prog[bar] + rng.choice([2, 4, 7])
            for i, _ in enumerate(rhythm):
                if i == 0:
                    d = prog[bar] + rng.choice([0, 2, 4, 7])        # strong beat: a chord tone
                else:
                    d += rng.choice([-2, -1, -1, 0, 1, 1, 2, 3])
                d = max(prog[bar] - 2, min(prog[bar] + 9, d))
                notes.append(d)
            bars.append(list(zip(rhythm, notes)))
        return bars

    phrase_a, phrase_b = make_phrase(p["prog_a"]), make_phrase(p["prog_b"])
    phrase_a2 = phrase_a[:3] + [make_phrase(p["prog_a"])[3]]       # A' varies its last bar
    # Song form after the intro: A A' B A (repeated), with an optional key change late on
    form = [("A", phrase_a, p["prog_a"]), ("A2", phrase_a2, p["prog_a"]),
            ("B", phrase_b, p["prog_b"]), ("A", phrase_a, p["prog_a"])]

    bar_len = steps * step
    total_bars = int(duration / bar_len) + 2
    n_total = int((total_bars * bar_len + 2) * SR)
    voices = {k: np.zeros(n_total) for k in ("lead", "arp", "bass", "drums", "pad", "fx")}
    fx_rng = random.Random(seed + 99)   # separate, so effects never change the melody
    noise = np.random.default_rng(seed).uniform(-1, 1, int(SR * 0.5))
    metal = np.sign(np.sin(np.arange(int(SR * 0.1)) * 0.9)) * 0.5 + noise[:int(SR * 0.1)] * 0.5

    def at(bar, s):
        swing = style["swing"] * step if s % 2 == 1 else 0.0
        return int((bar * bar_len + s * step + swing) * SR)

    key_change_bar = total_bars - 8 if p["key_change"] and total_bars > 14 else None
    prev_lead = None
    for bar in range(total_bars):
        intro = bar < p["intro_bars"]
        section_index = max(0, bar - p["intro_bars"]) // 4
        _, phrase, prog = form[section_index % len(form)]
        root = p["root"] + (2 if key_change_bar is not None and bar >= key_change_bar else 0)
        d = prog[max(0, bar - p["intro_bars"]) % 4]
        tones = chord(d, root)

        # Arpeggio / accompaniment
        if style["arp"]:
            kind, duty = style["arp"]
            rate = style["arp_rate"]
            for s in range(0, steps, rate):
                if style["bass"] == "waltz" and s % 4 != 0:
                    continue
                if style["bass"] == "waltz" and s == 0:
                    continue  # oom-pah: chords on beats 2 and 3
                note = tones[p["arp_shape"][(s // rate) % 4]] + 12 + 12 * octave_shift
                n = int(step * rate * SR)
                sig = _wave(kind, _phase(_freq(note), n), duty or 0.5) * _env(n, decay=0.07, sustain=0.15)
                _add(voices["arp"], at(bar, s), sig)

        # Bass
        bass_root = degree(d, -2, root)
        pattern = {
            "octave": [(s, 2, bass_root + (12 if s % 4 == 2 else 0)) for s in range(0, steps, 2)],
            "long": [(0, steps // 2, bass_root), (steps // 2, steps // 2, degree(d + 4, -2, root))],
            "drone": [(0, steps, bass_root)],
            "alternating": [(s, 4, bass_root if (s // 4) % 2 == 0 else degree(d + 4, -2, root)) for s in range(0, steps, 4)],
            "waltz": [(0, 4, bass_root)],
            "syncopated": [(0, 2, bass_root), (3, 2, bass_root + 12), (6, 2, bass_root), (10, 1, bass_root + 10),
                           (11, 2, bass_root + 12), (14, 2, degree(d + 4, -2, root))],
            "driving": [(s, 1, bass_root + (12 if s % 8 == 7 else 0)) for s in range(steps)],
            "soft": [(0, steps, bass_root + 12)],
        }[style["bass"]]
        if not (intro and style["bass"] in ("driving", "syncopated")):
            for s, length, note in pattern:
                if s >= steps:
                    continue
                n = int(step * length * SR)
                sig = _wave("triangle", _phase(_freq(note), n)) * _env(n, decay=0.25, sustain=0.6)
                _add(voices["bass"], at(bar, s), sig)

        # Drums
        if style["drums"]:
            kit = DRUMS[style["drums"]]
            for s in range(steps):
                pos = at(bar, s)
                if s in kit.get("kick", []):
                    n = int(0.12 * SR)
                    t = np.arange(n) / SR
                    _add(voices["drums"], pos, np.sin(2 * np.pi * (55 + 110 * np.exp(-t * 35)) * t) * np.exp(-t * 18))
                if intro:
                    continue
                if s in kit.get("snare", []):
                    n = int(0.12 * SR)
                    _add(voices["drums"], pos, noise[:n] * np.exp(-np.arange(n) / SR * 28) * 0.6)
                if s in kit.get("ghost", []):
                    n = int(0.05 * SR)
                    _add(voices["drums"], pos, noise[200:200 + n] * np.exp(-np.arange(n) / SR * 60) * 0.25)
                if s in kit.get("hat", []):
                    n = int(0.03 * SR)
                    accent = 0.22 if s % 4 == 0 else 0.14
                    _add(voices["drums"], pos, metal[:n] * np.exp(-np.arange(n) / SR * 150) * accent)
                if s in kit.get("open", []):
                    n = int(0.09 * SR)
                    _add(voices["drums"], pos, metal[:n] * np.exp(-np.arange(n) / SR * 30) * 0.15)

        # Soft held chord (slow attack, like a synth pad)
        if style.get("pad"):
            n = int(bar_len * SR)
            for note in tones[:3]:
                sig = _wave("pulse", _phase(_freq(note), n), 0.5) * _env(n, attack=0.35, decay=1.0, sustain=0.7, release=0.3)
                _add(voices["pad"], at(bar, 0), sig)

        # Sonar ping every other bar
        if style.get("ping") and bar % 2 == 0:
            n = int(1.4 * SR)
            t = np.arange(n) / SR
            sig = _wave("triangle", _phase(_freq(tones[0] + 36), n)) * np.exp(-t * 3.5)
            _add(voices["fx"], at(bar, 0), sig * 0.8)

        # Bubbles: quick rising blips
        if style.get("bubbles"):
            for s in range(steps):
                if fx_rng.random() < style["bubbles"]:
                    n = int(0.07 * SR)
                    t = np.arange(n) / SR
                    f0 = fx_rng.uniform(300, 600)
                    ph = np.cumsum(np.linspace(f0, f0 * fx_rng.uniform(2.2, 3.5), n) / SR) % 1.0
                    _add(voices["fx"], at(bar, s), _wave("pulse", ph, 0.25) * np.exp(-t * 35) * 0.5)

        # Lead melody (not during the intro)
        if not intro:
            for (start, length), deg in phrase[max(0, bar - p["intro_bars"]) % 4]:
                n = int(length * step * SR)
                note = degree(deg, 1 + octave_shift, root)
                f = _freq(note)
                glide = prev_lead if style["rhythm"] in ("long", "syncopated") else None
                vib = 0.006 if length >= 4 else 0.0
                sig = _wave(lead_kind, _phase(f, n, glide, vib), p["lead_duty"] or 0.5,
                            duty_sweep=lead_kind == "pulse" and length >= 6)
                sig = sig * _env(n, decay=0.35 if length >= 4 else 0.12, sustain=0.55)
                _add(voices["lead"], at(bar, start), sig)
                prev_lead = f

    if style["echo"]:
        voices["lead"] = _echo(voices["lead"], step * 3, style["echo"])
        voices["arp"] = _echo(voices["arp"], step * 2, style["echo"] * 0.7)
        voices["fx"] = _echo(voices["fx"], step * 3, min(0.6, style["echo"] + 0.15))

    levels = {"lead": 0.22, "arp": 0.12, "bass": 0.32, "drums": 0.34, "pad": 0.05, "fx": 0.12}
    if lead_kind == "triangle":
        levels["lead"] = 0.34
    if not style["drums"]:
        levels.update(arp=0.16, bass=0.26)
    mix = sum(voices[k] * v for k, v in levels.items())
    mix = mix[: int((duration + 0.5) * SR)]
    fade_in, fade_out = int(0.03 * SR), int(1.5 * SR)
    mix[:fade_in] *= np.linspace(0, 1, fade_in)
    mix[-fade_out:] *= np.linspace(1, 0, fade_out)
    mix = np.tanh(mix * 1.2)
    mix = mix / (np.max(np.abs(mix)) + 1e-9) * volume
    pcm = (mix * 32767).astype(np.int16)

    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())
    return path
