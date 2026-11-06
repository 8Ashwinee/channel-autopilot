"""`autopilot make`: video.yml -> out/<slug>/{voice.wav, timing.json, scene.html, <slug>.mp4, thumb.jpg} (+ a queue item)."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import yaml

from . import render, spec as specmod, template, voice


def make(path: str | Path, out_root: Path, still_at: float | None = None, no_render=False, check_only=False, workers=3) -> dict:
    sp = specmod.load(path)
    out = out_root / sp.slug
    out.mkdir(parents=True, exist_ok=True)
    print(f"voice ({sp.voice['name']}) ...")
    timing = voice.make(sp, out)
    html = out / "scene.html"
    html.write_text(template.build(sp, timing))
    total = timing["total"]
    print(f"timeline {total:.1f}s, {len(timing['scenes'])} scene(s)")
    problems = render.check(html, sp.size, timing)
    for p in problems:
        print("  LAYOUT:", p)
    if problems:
        raise SystemExit("layout problems: shorten the text or split the scene, then run again")
    if check_only:
        print("layout ok")
        return {"dir": out}
    first = timing["scenes"][sp.scenes[0]["id"]][0]
    thumb = out / "thumb.jpg"
    render.still(html, sp.size, still_at if still_at is not None else first + 2.2, thumb, resize=(1280, 720) if sp.kind == "video" else None)
    if still_at is not None or no_render:
        print("thumbnail:", thumb)
        return {"dir": out, "thumb": thumb}
    silent, mp4 = out / "silent.mp4", out / f"{sp.slug}.mp4"
    print("rendering frames ...")
    render.silent_video(html, sp.size, total, silent, workers=workers)
    render.mux(silent, out / "voice.wav", sp.music, sp.music_gain, total, mp4)
    silent.unlink(missing_ok=True)
    print("video:", mp4)
    return {"dir": out, "video": mp4, "thumb": thumb, "spec": sp, "total": total}


def to_queue(sp, result: dict, queue_dir: Path) -> Path:
    d = queue_dir / sp.slug
    d.mkdir(parents=True, exist_ok=True)
    shutil.copy(result["video"], d / "video.mp4")
    shutil.copy(result["thumb"], d / "thumb.jpg")
    item = {"kind": sp.kind, "title": sp.title, "description": sp.d.get("description", ""), "tags": sp.d.get("tags", []),
            "files": {"video": "video.mp4", "thumbnail": "thumb.jpg"}}
    for k in ("caption", "playlist", "priority", "language"):   # optional extras a video.yml may carry into the queue item
        if sp.d.get(k) not in (None, ""):
            item[k] = sp.d[k]
    if sp.kind == "video":
        item["actions"] = sp.d.get("actions", ["youtube.video"])
    (d / "item.yml").write_text(yaml.safe_dump(item, sort_keys=False, allow_unicode=True))
    return d
