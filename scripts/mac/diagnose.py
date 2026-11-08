"""Check each part of the video pipeline separately on this Mac.

Run from the project folder with the venv active:
    python scripts/mac/diagnose.py

Each check runs in its own process, so a hard crash (segmentation fault,
abort) in one library is reported as CRASH without stopping the others.
Paste the whole output when asking for help.
"""
import os
import platform
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRATCH = os.path.join(ROOT, ".mp")
os.makedirs(SCRATCH, exist_ok=True)

CHECKS = [
    ("numpy", "import numpy; print(numpy.__version__)"),
    ("onnxruntime", "import onnxruntime as o; print(o.__version__, o.get_available_providers())"),
    ("ctranslate2", "import ctranslate2 as c; print(c.__version__)"),
    ("espeak (phonetics)",
     "import espeakng_loader, ctypes; ctypes.cdll.LoadLibrary(espeakng_loader.get_library_path()); print('loaded')"),
    ("voice model (KittenTTS)",
     "import sys; sys.path.insert(0, 'src'); from classes.Tts import TTS; "
     f"TTS().synthesize('Testing one two three.', {os.path.join(SCRATCH, 'diag.wav')!r}); print('wav written')"),
    ("subtitles (Whisper)",
     "from faster_whisper import WhisperModel; "
     "m = WhisperModel('base', device='cpu', compute_type='int8'); "
     f"segs, _ = m.transcribe({os.path.join(SCRATCH, 'diag.wav')!r}, vad_filter=True); "
     "print(repr(' '.join(s.text for s in segs).strip()))"),
    ("voice + subtitles in one process",
     "import sys; sys.path.insert(0, 'src'); from classes.Tts import TTS; t = TTS(); "
     "from faster_whisper import WhisperModel; m = WhisperModel('base', device='cpu', compute_type='int8'); "
     f"t.synthesize('Second test.', {os.path.join(SCRATCH, 'diag2.wav')!r}); "
     f"segs, _ = m.transcribe({os.path.join(SCRATCH, 'diag2.wav')!r}); print(repr(' '.join(s.text for s in segs).strip()))"),
    ("8-bit frame",
     "import sys; sys.path.insert(0, 'src'); import pixel_art as pa; "
     "f = pa.render_frame({'scene': 'planet', 'preset': 'venus'}, 1.0, 1, 'Test', 'WonderBytes', 'FACT 1 / 1'); print(f.shape)"),
    ("video encoder (MoviePy + ffmpeg)",
     "import numpy as np; from moviepy.editor import ImageClip; "
     f"ImageClip(np.zeros((64, 64, 3), 'uint8')).set_duration(1).write_videofile({os.path.join(SCRATCH, 'diag.mp4')!r}, fps=12, logger=None); print('mp4 written')"),
]


def run(code, env_extra):
    env = dict(os.environ, PYTHONFAULTHANDLER="1", HF_HUB_DISABLE_TELEMETRY="1", **env_extra)
    start = time.time()
    p = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True, timeout=1800)
    secs = time.time() - start
    if p.returncode == 0:
        last = (p.stdout.strip().splitlines() or [""])[-1]
        return f"OK      ({secs:.0f}s) {last[:90]}"
    kind = {-11: "CRASH (segmentation fault)", -6: "CRASH (abort)", 139: "CRASH (segmentation fault)", 134: "CRASH (abort)"}
    lines = [l for l in (p.stderr or "").splitlines() if l.strip() and "Warning" not in l][-6:]
    return f"{kind.get(p.returncode, f'FAILED (exit {p.returncode})')}\n" + "\n".join("          " + l[:150] for l in lines)


print(f"macOS {platform.mac_ver()[0]} {platform.machine()}, Python {platform.python_version()}")
print(f"KMP_DUPLICATE_LIB_OK={os.environ.get('KMP_DUPLICATE_LIB_OK', '(not set)')}\n")
for name, code in CHECKS:
    print(f"{name:34} ", end="", flush=True)
    print(run(code, {"KMP_DUPLICATE_LIB_OK": "TRUE"}))

print("\nSame voice + subtitles check, one thread each (rules out a threading clash):")
print(f"{'voice + subtitles, 1 thread':34} ", end="", flush=True)
print(run(CHECKS[6][1], {"KMP_DUPLICATE_LIB_OK": "TRUE", "OMP_NUM_THREADS": "1"}))
