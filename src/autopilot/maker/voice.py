"""Speech with Kokoro (open-weight text-to-speech, Apache-2.0, runs on the CPU), and the timeline built FROM the speech:
a line starts when it is spoken, a scene ends when its last line ends, so pictures and voice cannot drift apart.

Needs the `maker` extra, espeak-ng (brew install espeak-ng / apt install espeak-ng) and the model files (autopilot make --setup)."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

from ..errors import ConfigError

SR = 48000
RELEASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
MODEL_FILES = ("kokoro-v1.0.onnx", "voices-v1.0.bin")


def model_dir() -> Path:
    return Path(os.environ.get("AUTOPILOT_VOICE_DIR", Path.home() / ".cache" / "channel-autopilot" / "voice"))


def setup():
    d = model_dir()
    d.mkdir(parents=True, exist_ok=True)
    for f in MODEL_FILES:
        if not (d / f).exists() or not (d / f).stat().st_size:
            print(f"downloading {f} (~{'300' if f.endswith('onnx') else '25'} MB) ...")
            subprocess.run(["curl", "-fL", "-o", str(d / f), f"{RELEASE}/{f}"], check=True)
    return d


def _espeak():
    if os.environ.get("PHONEMIZER_ESPEAK_LIBRARY"):
        return
    for c in ("/opt/homebrew/opt/espeak-ng/lib/libespeak-ng.1.dylib", "/usr/local/opt/espeak-ng/lib/libespeak-ng.1.dylib",
              "/usr/lib/x86_64-linux-gnu/libespeak-ng.so.1", "/usr/lib/aarch64-linux-gnu/libespeak-ng.so.1"):
        if Path(c).exists():
            os.environ["PHONEMIZER_ESPEAK_LIBRARY"] = c
            return


def make(spec, out: Path, gap=0.45, scene_gap=0.7, lead=0.8, tail=0.9, end_hold=1.5):
    """-> timing dict; writes out/voice.wav"""
    try:
        import numpy as np
        import soundfile as sf
        from kokoro_onnx import Kokoro
    except ImportError:
        raise ConfigError("the video maker needs: pip install 'channel-autopilot[maker]'") from None
    if not shutil.which("ffmpeg"):
        raise ConfigError("ffmpeg is not installed (it is not bundled: brew install ffmpeg / apt install ffmpeg)")
    d = model_dir()
    if not all((d / f).exists() for f in MODEL_FILES):
        raise ConfigError("voice model files missing: run `autopilot make --setup`")
    _espeak()
    out.mkdir(parents=True, exist_ok=True)
    cache = out / "voice-cache"
    cache.mkdir(exist_ok=True)
    k = Kokoro(str(d / MODEL_FILES[0]), str(d / MODEL_FILES[1]))
    v = spec.voice

    def synth(text):
        key = hashlib.sha1(json.dumps([text, v["name"], v["lang"], v["speed"]]).encode()).hexdigest()[:16]
        wav = cache / f"{key}.wav"
        if not wav.exists():
            s, sr = k.create(text, voice=v["name"], speed=float(v["speed"]), lang=v["lang"])
            raw = cache / f"{key}.raw.wav"
            sf.write(raw, s, sr)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-ar", str(SR), "-ac", "1", str(wav)], check=True)
            raw.unlink()
        y, _ = sf.read(wav, dtype="float32")
        on = np.nonzero(np.abs(y) > 0.01)[0]
        return y[max(0, on[0] - 480): on[-1] + 2400] if len(on) else y

    t, clips, scenes, beats = 0.0, [], {}, {}
    for si, sc in enumerate(spec.all_scenes()):
        if si:
            t += scene_gap
        s0 = t
        t += lead
        lines = []
        for bi, line in enumerate(sc["say"]):
            text, pause = (line["text"], float(line.get("pause", 0))) if isinstance(line, dict) else (line, 0.0)
            if bi:
                t += gap
            y = synth(text)
            clips.append((t, y))
            lines.append({"t0": round(t, 3), "t1": round(t + len(y) / SR, 3), "text": text})
            t += len(y) / SR + pause
        t += tail
        scenes[sc["id"]] = [round(s0, 3), round(t, 3)]
        beats[sc["id"]] = lines
    total = round(t + end_hold, 3)
    voice = np.zeros(int(total * SR) + SR, np.float32)
    for t0, y in clips:
        i = int(t0 * SR)
        voice[i:i + len(y)] += y
    voice = voice[: int(total * SR)]
    voice /= max(1e-6, np.abs(voice).max() / 0.89)
    sf.write(out / "voice.wav", voice, SR)
    timing = {"total": total, "scenes": scenes, "beats": beats}
    (out / "timing.json").write_text(json.dumps(timing, indent=1))
    return timing
