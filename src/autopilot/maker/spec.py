"""video.yml: load and validate.

slug: stop-doomscrolling
kind: short                 # short = 1080x1920 (9:16, up to ~60 s), video = 1920x1080
title: Stop doom-scrolling in three steps
description: ...
tags: [focus, habits]
theme: {preset: calm}       # calm | bold | light, then any of: bg, bg2, fg, muted, accent, accent2, font
voice: {name: af_heart, speed: 1.0, lang: en-us}
captions: true              # burned-in captions band
music: bed.mp3              # optional, relative to video.yml; ducked under the voice
music_gain: 0.18
scenes:
  - id: hook
    headline: Stop doom-scrolling
    sub: Three steps that actually work
    say: [You pick up your phone for one thing., Forty minutes later you are still there.]
  - id: steps
    headline: The three steps
    bullets: [Move the app off your home screen, Set a ten minute timer, Put the phone in another room]
    say: [First, move the app., Second, set a timer., Third, leave the phone in another room.]   # bullet i appears with line i
    image: optional.png
outro: {headline: Follow for more, sub: "@yourchannel", say: [Follow for more.]}
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from ..errors import ConfigError

SIZES = {"short": (1080, 1920), "video": (1920, 1080)}
PRESETS = {
    "calm":  {"bg": "#0b1e33", "bg2": "#1b4965", "fg": "#f4f8fb", "muted": "#a9c1d4", "accent": "#5fb3d9", "accent2": "#7be0b5", "font": "Inter, 'Helvetica Neue', Arial, sans-serif"},
    "bold":  {"bg": "#111111", "bg2": "#2b1d4a", "fg": "#ffffff", "muted": "#c9c2d8", "accent": "#ffd23f", "accent2": "#ff5d73", "font": "Inter, 'Helvetica Neue', Arial, sans-serif"},
    "light": {"bg": "#f7f9fc", "bg2": "#e3ecf6", "fg": "#14213d", "muted": "#5b6b82", "accent": "#2563eb", "accent2": "#16a34a", "font": "Inter, 'Helvetica Neue', Arial, sans-serif"},
}
COLOUR = re.compile(r"^#[0-9a-fA-F]{6}$")


class Spec:
    def __init__(self, d: dict, base: Path):
        self.d, self.base = d, base
        self.slug = d["slug"]
        self.kind = d["kind"]
        self.size = SIZES[self.kind]
        self.title = d.get("title", self.slug)
        self.theme = {**PRESETS[(d.get("theme") or {}).get("preset", "calm")], **{k: v for k, v in (d.get("theme") or {}).items() if k != "preset"}}
        self.voice = {"name": "af_heart", "speed": 1.0, "lang": "en-us", **(d.get("voice") or {})}
        self.captions = bool(d.get("captions", True))
        self.music = (base / d["music"]) if d.get("music") else None
        self.music_gain = float(d.get("music_gain", 0.18))
        self.scenes = list(d["scenes"])
        self.outro = d.get("outro")

    def all_scenes(self) -> list[dict]:
        s = list(self.scenes)
        if self.outro:
            s.append({"id": "outro", **self.outro})
        return s


def load(path: str | Path) -> Spec:
    p = Path(path)
    d = yaml.safe_load(p.read_text()) or {}
    for k in ("slug", "kind", "scenes"):
        if k not in d:
            raise ConfigError(f"{p}: missing {k}")
    if d["kind"] not in SIZES:
        raise ConfigError(f"{p}: kind must be short or video")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", d["slug"]):
        raise ConfigError(f"{p}: slug must be lower-case letters, digits and hyphens")
    th = d.get("theme") or {}
    if th.get("preset", "calm") not in PRESETS:
        raise ConfigError(f"{p}: theme.preset must be one of {list(PRESETS)}")
    for k in ("bg", "bg2", "fg", "muted", "accent", "accent2"):
        if k in th and not COLOUR.match(str(th[k])):
            raise ConfigError(f"{p}: theme.{k} must be a #rrggbb colour")
    ids = set()
    for s in d["scenes"] + ([{"id": "outro", **d["outro"]}] if d.get("outro") else []):
        if not s.get("id") or s["id"] in ids:
            raise ConfigError(f"{p}: every scene needs a unique id (got {s.get('id')!r})")
        ids.add(s["id"])
        if not s.get("say"):
            raise ConfigError(f"{p}: scene {s['id']} needs `say` (the lines the voice speaks)")
        if not (s.get("headline") or s.get("bullets") or s.get("image")):
            raise ConfigError(f"{p}: scene {s['id']} shows nothing: give it a headline, bullets or an image")
        if s.get("image") and not (p.parent / s["image"]).exists():
            raise ConfigError(f"{p}: image not found: {s['image']}")
    if d.get("music") and not (p.parent / d["music"]).exists():
        raise ConfigError(f"{p}: music not found: {d['music']}")
    return Spec(d, p.parent)
