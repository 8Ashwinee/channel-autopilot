"""Chromium draws each frame from the scene's renderAt(t); ffmpeg turns the frames into video and adds the voice."""
from __future__ import annotations

import io
import json
import shutil
import subprocess
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from ..errors import AutopilotError, ConfigError

FPS = 30


def _open(p, html: Path, size):
    b = p.chromium.launch(args=["--no-sandbox"])
    pg = b.new_page(viewport={"width": size[0], "height": size[1]})
    pg.goto(html.resolve().as_uri())
    pg.evaluate("window.init ? window.init() : true")
    pg.wait_for_timeout(150)
    return b, pg


def _need_playwright():
    try:
        from playwright.sync_api import sync_playwright
        return sync_playwright
    except ImportError:
        raise ConfigError("the video maker needs: pip install 'channel-autopilot[maker]' && playwright install chromium") from None


def still(html: Path, size, t: float, out: Path, resize=None):
    from PIL import Image
    sp = _need_playwright()
    with sp() as p:
        b, pg = _open(p, html, size)
        pg.evaluate(f"renderAt({t})")
        png = pg.screenshot()
        b.close()
    im = Image.open(io.BytesIO(png)).convert("RGB")
    if resize:
        im = im.resize(resize, Image.LANCZOS)
    im.save(out, quality=92)


CHECK_JS = """() => { const W = innerWidth, H = innerHeight, bad = [];
  for (const el of document.querySelectorAll('h1,.sub,li,.pic,#cap')) {
    if (+getComputedStyle(el.closest('.scene') || el).opacity < .5 && el.id !== 'cap') continue;
    if (getComputedStyle(el).opacity === '0') continue;
    const r = el.getBoundingClientRect(); if (!r.width) continue;
    if (r.left < -2 || r.right > W + 2 || r.top < -2 || r.bottom > H + 2) bad.push([el.tagName + ' ' + (el.textContent || '').trim().slice(0, 40), 'outside the frame']);
  }
  for (const sc of document.querySelectorAll('.scene')) if (+sc.style.opacity > .5 && sc.scrollHeight > sc.clientHeight + 4)
    bad.push([(sc.textContent || '').trim().slice(0, 40), 'more content than fits in its area']);
  return bad; }"""


def check(html: Path, size, timing) -> list:
    """Layout check at the end of each scene's fade-in: text off the frame, or a scene with more than fits."""
    sp = _need_playwright()
    found = []
    with sp() as p:
        b, pg = _open(p, html, size)
        for sid, (s0, s1) in timing["scenes"].items():
            t = s1 - 0.7
            pg.evaluate(f"renderAt({t})")
            for what, why in pg.evaluate(CHECK_JS):
                found.append(f"scene {sid}: {why}: {what}")
        b.close()
    return found


def _chunk(args):
    html, size, a, b_, out = args
    sp = _need_playwright()
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-i", "-",
                           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(out)], stdin=subprocess.PIPE)
    with sp() as p:
        br, pg = _open(p, Path(html), size)
        for i in range(a, b_):
            pg.evaluate(f"renderAt({i / FPS})")
            ff.stdin.write(pg.screenshot(type="jpeg", quality=92))
        br.close()
    ff.stdin.close()
    if ff.wait():
        raise AutopilotError("ffmpeg failed while encoding frames")
    return str(out)


def silent_video(html: Path, size, total: float, out: Path, workers=3):
    n = int(total * FPS)
    cuts = [round(n * i / workers) for i in range(workers + 1)]
    with tempfile.TemporaryDirectory() as td:
        jobs = [(str(html), size, cuts[i], cuts[i + 1], Path(td) / f"c{i}.mp4") for i in range(workers) if cuts[i + 1] > cuts[i]]
        with ProcessPoolExecutor(len(jobs)) as ex:
            parts = list(ex.map(_chunk, jobs))
        lst = Path(td) / "list.txt"
        lst.write_text("".join(f"file '{p}'\n" for p in parts))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out)], check=True)


def mux(silent: Path, voice: Path, music: Path | None, gain: float, total: float, out: Path):
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(silent), "-i", str(voice)]
    if music:
        cmd += ["-i", str(music)]
        f = (f"[1:a]asplit[v1][v2];[2:a]aloop=loop=-1:size=2e9,atrim=0:{total},afade=t=in:d=1.5,afade=t=out:st={max(0, total - 2.5):.2f}:d=2.5,volume={gain}[m];"
             f"[m][v2]sidechaincompress=threshold=0.04:ratio=10:attack=20:release=400[md];[v1][md]amix=inputs=2:normalize=0,loudnorm=I=-16:TP=-1.5[a]")
    else:
        f = "[1:a]loudnorm=I=-16:TP=-1.5[a]"
    cmd += ["-filter_complex", f, "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)
