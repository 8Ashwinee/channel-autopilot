"""The queue: a folder of items. Each item is a folder with an item.yml and its files.

  queue/my-first-short/item.yml
  queue/my-first-short/video.mp4
  queue/my-first-short/thumb.jpg

item.yml:
  kind: short | video | image | post
  title: ...
  description: ...           # YouTube description / default caption
  caption: ...               # Instagram + Facebook caption (falls back to description)
  tags: [a, b]
  link: https://...          # for kind: post (a link card)
  priority: 10               # lower runs first; default 100
  files: {video: video.mp4, thumbnail: thumb.jpg, image: image.png}   # relative to the item folder
  actions: [youtube.short, instagram.reel]   # optional; defaults come from the config by kind
  language: en
  playlist: PLxxxx           # optional YouTube playlist id
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .errors import ConfigError

KINDS = ("short", "video", "image", "post")
KNOWN_ACTIONS = ("youtube.short", "youtube.video", "instagram.reel", "instagram.story", "instagram.image",
                 "facebook.reel", "facebook.story", "facebook.image", "facebook.post")
NEEDS = {  # which file each action needs
    "youtube.short": "video", "youtube.video": "video", "instagram.reel": "video", "instagram.story": "video",
    "facebook.reel": "video", "facebook.story": "video", "instagram.image": "image", "facebook.image": "image",
}


@dataclass
class Item:
    slug: str
    dir: Path
    kind: str
    title: str = ""
    description: str = ""
    caption: str = ""
    tags: list = field(default_factory=list)
    link: str = ""
    priority: int = 100
    files: dict = field(default_factory=dict)
    actions: list = field(default_factory=list)
    language: str = "en"
    playlist: str = ""

    def text(self) -> str:
        return self.caption or self.description or self.title


def load_item(folder: Path, default_actions: dict) -> Item:
    y = folder / "item.yml"
    if not y.exists():
        raise ConfigError(f"{folder}: no item.yml")
    d = yaml.safe_load(y.read_text()) or {}
    kind = d.get("kind")
    if kind not in KINDS:
        raise ConfigError(f"{y}: kind must be one of {KINDS}, got {kind!r}")
    files = {k: (folder / v) for k, v in (d.get("files") or {}).items()}
    actions = list(d.get("actions") or default_actions.get(kind, []))
    for a in actions:
        if a not in KNOWN_ACTIONS:
            raise ConfigError(f"{y}: unknown action {a!r}")
        need = NEEDS.get(a)
        if need and not files.get(need):
            raise ConfigError(f"{y}: action {a} needs files.{need}")
        if need and not files[need].exists():
            raise ConfigError(f"{y}: file not found: {files[need]}")
        if a == "facebook.post" and not (d.get("link") or d.get("caption") or d.get("description")):
            raise ConfigError(f"{y}: facebook.post needs a link, caption or description")
    return Item(slug=folder.name, dir=folder, kind=kind, title=d.get("title", ""), description=d.get("description", ""),
                caption=d.get("caption", ""), tags=list(d.get("tags") or []), link=d.get("link", ""),
                priority=int(d.get("priority", 100)), files=files, actions=actions,
                language=d.get("language", "en"), playlist=d.get("playlist", ""))


def load_queue(root: Path, default_actions: dict) -> list[Item]:
    if not root.exists():
        return []
    items = [load_item(p, default_actions) for p in sorted(root.iterdir()) if p.is_dir() and (p / "item.yml").exists()]
    return sorted(items, key=lambda i: (i.priority, i.slug))
