"""Config: one YAML file. ${ENV_VAR} anywhere in a string is replaced from the environment."""
from __future__ import annotations

import os
import re
from pathlib import Path

import yaml

from .errors import ConfigError

DEFAULT_LIMITS = {
    "youtube.short": 2,
    "youtube.video": 2,
    "instagram.reel": 1,
    "instagram.story": 1,
    "instagram.image": 1,
    "facebook.reel": 1,
    "facebook.story": 1,
    "facebook.image": 1,
    "facebook.post": 1,
}

DEFAULT_ACTIONS = {
    "short": ["youtube.short", "instagram.reel", "instagram.story", "facebook.reel", "facebook.story"],
    "video": ["youtube.video"],
    "image": ["instagram.image", "facebook.image"],
    "post": ["facebook.post"],
}

_ENV = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


def _expand(v):
    if isinstance(v, str):
        return _ENV.sub(lambda m: os.environ.get(m.group(1), m.group(2) if m.group(2) is not None else ""), v)
    if isinstance(v, dict):
        return {k: _expand(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_expand(x) for x in v]
    return v


class Config:
    def __init__(self, data: dict, base: Path):
        self.data = data
        self.base = base

    @classmethod
    def load(cls, path: str | Path) -> "Config":
        p = Path(path).expanduser()
        if not p.exists():
            raise ConfigError(f"config not found: {p} (run `autopilot init`)")
        data = _expand(yaml.safe_load(p.read_text()) or {})
        return cls(data, p.parent.resolve())

    def get(self, dotted: str, default=None):
        cur = self.data
        for part in dotted.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return default
            cur = cur[part]
        return cur if cur is not None else default

    def path(self, dotted: str, default: str) -> Path:
        p = Path(str(self.get(dotted, default))).expanduser()
        return p if p.is_absolute() else (self.base / p)

    @property
    def limits(self) -> dict:
        return {**DEFAULT_LIMITS, **(self.get("limits", {}) or {})}

    @property
    def actions_for(self) -> dict:
        return {**DEFAULT_ACTIONS, **(self.get("default_actions", {}) or {})}
