import pytest
import yaml

from autopilot.config import Config
from autopilot.state import Ledger


@pytest.fixture
def cfg(tmp_path):
    data = {"name": "Test", "timezone": "UTC",
            "limits": {"youtube.short": 2, "instagram.reel": 1, "facebook.post": 1},
            "instagram": {"account_id": "IG1", "token": "tok"}, "facebook": {"page_id": "PG1", "token": "tok"},
            "media": {"command": "echo https://cdn.example.com/{name}"}}
    return Config(data, tmp_path)


@pytest.fixture
def ledger():
    return Ledger(":memory:")


def make_item(root, slug, kind="short", **extra):
    d = root / slug
    d.mkdir(parents=True)
    (d / "v.mp4").write_bytes(b"x")
    (d / "t.jpg").write_bytes(b"x")
    y = {"kind": kind, "title": slug, "description": "d", "files": {"video": "v.mp4", "thumbnail": "t.jpg"}}
    y.update(extra)
    (d / "item.yml").write_text(yaml.safe_dump(y))
    return d
