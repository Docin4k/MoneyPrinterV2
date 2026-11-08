"""Original chiptune background music, generated from a seed.

Each seed gives a different track: key, tempo, mode, chord progression,
arpeggio and drum patterns, and a lead melody built from repeating phrases
(A A B A). Voices use classic 8-bit waveforms: pulse waves for lead and
arpeggio, a triangle wave for bass and noise for drums.

Usage:
    from chiptune import generate_track
    generate_track("music.wav", duration=45, seed=1234)
"""
import random
import wave
import zlib

import numpy as np

SR = 44100

MODES = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
}

# Chord roots as scale degrees (0 = tonic), one chord per bar
PROGRESSIONS = {
    "major": [[0, 4, 5, 3], [0, 5, 3, 4], [5, 3, 0, 4], [0, 3, 5, 4], [0, 3, 0, 4]],
    "minor": [[0, 5, 2, 6], [0, 3, 5, 4], [0, 6, 5, 6], [0, 5, 3, 4]],
    "dorian": [[0, 3, 0, 3], [0, 6, 3, 0], [0, 1, 3, 4]],
    "mixolydian": [[0, 6, 3, 0], [0, 3, 6, 0], [0, 6, 0, 4]],
}

RHYTHMS = [  # lead rhythms for one bar, in 16th-note steps (start, length)
    [(0, 4), (4, 2), (6, 2), (8, 4), (12, 4)],
    [(0, 2), (2, 2), (4, 4), (10, 2), (12, 4)],
    [(0, 6), (6, 2), (8, 2), (10, 2), (12, 4)],
    [(0, 3), (3, 3), (6, 2), (8, 8)],
    [(2, 2), (4, 2), (6, 2), (8, 4), (12, 2), (14, 2)],
]


def seed_from_text(text: str) -> int:
    return zlib.crc32(text.encode("utf-8"))


def _freq(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def _pulse(freq, n, duty):
    phase = (np.arange(n) * freq / SR) % 1.0
    return np.where(phase < duty, 1.0, -1.0)


def _triangle(freq, n):
    phase = (np.arange(n) * freq / SR) % 1.0
    return 4 * np.abs(phase - 0.5) - 1


def _env(n, attack=0.004, decay=0.25, sustain=0.6, release=0.03):
    t = np.arange(n) / SR
    env = np.minimum(1.0, t / attack) * (sustain + (1 - sustain) * np.exp(-t / decay))
    rel = int(release * SR)
    if rel and n > rel:
        env[-rel:] *= np.linspace(1, 0, rel)
    return env


def _add(buf, start, sig):
    end = min(len(buf), start + len(sig))
    if start < end:
        buf[start:end] += sig[:end - start]


def generate_track(path: str, duration: float, seed: int, volume: float = 0.8) -> str:
    """Write a WAV file of at least `duration` seconds and return its path."""
    rng = random.Random(seed)
    mode = rng.choice(list(MODES))
    scale = MODES[mode]
    root = rng.randint(57, 64)                 # A3..E4
    bpm = rng.randint(100, 136)
    step = 60.0 / bpm / 4                      # one 16th note, seconds
    prog = rng.choice(PROGRESSIONS[mode])
    duty_lead = rng.choice([0.25, 0.5])
    duty_arp = rng.choice([0.125, 0.25])
    arp_shape = rng.choice([[0, 1, 2, 1], [0, 1, 2, 3], [0, 2, 1, 2], [2, 1, 0, 1]])
    hat_every = rng.choice([2, 2, 1])

    def degree(d, octave=0):
        return root + scale[d % 7] + 12 * (d // 7 + octave)

    def chord(d):
        return [degree(d), degree(d + 2), degree(d + 4), degree(d + 7)]

    # Melody phrases: A and B, each one bar per chord, reused A A B A
    def make_phrase():
        bars = []
        for bar in range(4):
            rhythm = rng.choice(RHYTHMS)
            notes, d = [], prog[bar] + rng.choice([2, 4, 7])
            for _ in rhythm:
                d += rng.choice([-2, -1, -1, 0, 1, 1, 2])
                d = max(prog[bar], min(prog[bar] + 9, d))
                notes.append(d)
            bars.append(list(zip(rhythm, notes)))
        return bars

    phrase_a, phrase_b = make_phrase(), make_phrase()
    form = [phrase_a, phrase_a, phrase_b, phrase_a]

    total_bars = int(duration / (step * 16)) + 2
    n_total = int((total_bars * 16 * step + 1) * SR)
    lead = np.zeros(n_total)
    arp = np.zeros(n_total)
    bass = np.zeros(n_total)
    drums = np.zeros(n_total)
    noise = np.random.default_rng(seed).uniform(-1, 1, int(SR * 0.3))

    for bar in range(total_bars):
        d = prog[bar % 4]
        tones = chord(d)
        bar_start = bar * 16 * step
        section = (bar // 4) % 4

        # Arpeggio: 16th notes through chord tones
        for s in range(16):
            note = tones[arp_shape[s % 4]] + 12
            n = int(step * SR)
            sig = _pulse(_freq(note), n, duty_arp) * _env(n, decay=0.06, sustain=0.2)
            _add(arp, int((bar_start + s * step) * SR), sig)

        # Bass: eighth notes, root with an octave jump on the off-beats
        for s in range(0, 16, 2):
            note = degree(d, -2) + (12 if s % 4 == 2 and rng.random() < 0.5 else 0)
            n = int(step * 2 * SR)
            sig = _triangle(_freq(note), n) * _env(n, decay=0.2, sustain=0.5)
            _add(bass, int((bar_start + s * step) * SR), sig)

        # Drums: kick on 1 and 3, snare on 2 and 4, hats
        for s in range(16):
            pos = int((bar_start + s * step) * SR)
            if s in (0, 8) or (s == 10 and rng.random() < 0.3):
                n = int(0.12 * SR)
                t = np.arange(n) / SR
                kick = np.sin(2 * np.pi * (60 + 120 * np.exp(-t * 35)) * t) * np.exp(-t * 18)
                _add(drums, pos, kick)
            if s in (4, 12):
                n = int(0.12 * SR)
                _add(drums, pos, noise[:n] * np.exp(-np.arange(n) / SR * 30) * 0.6)
            if s % hat_every == 0:
                n = int(0.03 * SR)
                _add(drums, pos, noise[100:100 + n] * np.exp(-np.arange(n) / SR * 150) * 0.25)

        # Lead melody enters after the first 4 bars
        if bar >= 4:
            for (start, length), deg in form[section][bar % 4]:
                n = int(length * step * SR)
                note = degree(deg, 1)
                t = np.arange(n) / SR
                vib = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * t) * np.minimum(1, t / 0.15)
                phase = np.cumsum(_freq(note) * vib / SR) % 1.0
                sig = np.where(phase < duty_lead, 1.0, -1.0) * _env(n, decay=0.3, sustain=0.55)
                _add(lead, int((bar_start + start * step) * SR), sig)

    mix = 0.22 * lead + 0.12 * arp + 0.35 * bass + 0.35 * drums
    mix = mix[: int((duration + 0.5) * SR)]
    fade = int(1.5 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)
    mix = np.tanh(mix * 1.2)
    mix = mix / (np.max(np.abs(mix)) + 1e-9) * volume
    pcm = (mix * 32767).astype(np.int16)

    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())
    return path


def describe(seed: int) -> str:
    """Human-readable summary of the track a seed produces."""
    rng = random.Random(seed)
    mode = rng.choice(list(MODES))
    root = rng.randint(57, 64)
    bpm = rng.randint(100, 136)
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    return f"{names[root % 12]} {mode}, {bpm} BPM"
