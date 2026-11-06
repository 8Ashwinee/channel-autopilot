import pytest

from autopilot import http
from autopilot.errors import AutopilotError, ConfigError, QuotaReached
from autopilot.platforms import facebook, instagram
from autopilot.queue import Item
from autopilot.schedule import Ctx
from pathlib import Path


def item(**kw):
    base = dict(slug="s", dir=Path("."), kind="short", title="T", description="D", caption="Cap", files={"video": Path("v.mp4"), "image": Path("i.png")})
    base.update(kw)
    return Item(**base)


class Fake:
    """Records calls and answers like the Graph API."""
    def __init__(self, answers): self.calls, self.answers = [], answers
    def __call__(self, method, url, data=None, headers=None, **kw):
        self.calls.append((method, url, dict(data or {})))
        for needle, ans in self.answers:
            if needle in url:
                return ans(data) if callable(ans) else ans
        raise AssertionError(f"unexpected call {method} {url}")


def test_instagram_reel_flow(cfg, monkeypatch):
    f = Fake([("IG1/media_publish", {"id": "M1"}), ("IG1/media", {"id": "C1"}), ("/C1", {"status_code": "FINISHED"}),
              ("/M1", {"permalink": "https://www.instagram.com/reel/abc/"})])
    monkeypatch.setattr(http, "request", f)
    r = instagram.reel(Ctx(cfg), item())
    assert r.url == "https://www.instagram.com/reel/abc/" and r.remote_id == "M1"
    first = f.calls[0][2]
    assert first["media_type"] == "REELS" and first["video_url"].startswith("https://cdn.example.com/s-v.mp4") and first["caption"] == "Cap"


def test_instagram_story_uses_stories_media_type(cfg, monkeypatch):
    f = Fake([("IG1/media_publish", {"id": "M1"}), ("IG1/media", {"id": "C1"}), ("/C1", {"status_code": "FINISHED"}), ("/M1", {"permalink": "u"})])
    monkeypatch.setattr(http, "request", f)
    instagram.story(Ctx(cfg), item())
    assert f.calls[0][2]["media_type"] == "STORIES" and "caption" not in f.calls[0][2]


def test_instagram_quota_is_not_a_failure(cfg, monkeypatch):
    def lim(*a, **k): raise AutopilotError("HTTP 400 content_publishing_limit reached")
    monkeypatch.setattr(http, "request", lim)
    with pytest.raises(QuotaReached):
        instagram.reel(Ctx(cfg), item())


def test_instagram_container_error_raises(cfg, monkeypatch):
    f = Fake([("IG1/media", {"id": "C1"}), ("/C1", {"status_code": "ERROR", "status": "bad video"})])
    monkeypatch.setattr(http, "request", f)
    with pytest.raises(AutopilotError, match="ERROR"):
        instagram.reel(Ctx(cfg), item())


def test_facebook_reel_flow(cfg, monkeypatch):
    facebook._page_token._c = {}
    f = Fake([("PG1/videos", {"id": "V1"}), ("PG1", {"access_token": "PAGE"}),
              ("/V1", {"status": {"video_status": "ready"}, "permalink_url": "/reel/V1/"})])
    monkeypatch.setattr(http, "request", f)
    r = facebook.reel(Ctx(cfg), item())
    assert r.url == "https://www.facebook.com/reel/V1/"
    post_call = [c for c in f.calls if c[0] == "POST"][0]
    assert post_call[2]["access_token"] == "PAGE" and post_call[2]["description"] == "Cap"


def test_facebook_post_with_link(cfg, monkeypatch):
    facebook._page_token._c = {}
    f = Fake([("PG1/feed", {"id": "PG1_9"}), ("PG1_9", {"permalink_url": "https://www.facebook.com/PG1/posts/9"}), ("PG1", {"access_token": "PAGE"})])
    monkeypatch.setattr(http, "request", f)
    r = facebook.post(Ctx(cfg), item(link="https://example.com/blog"))
    assert r.url.endswith("/posts/9")
    assert [c for c in f.calls if c[0] == "POST"][0][2]["link"] == "https://example.com/blog"


def test_missing_credentials_are_a_config_error(cfg):
    cfg.data["instagram"] = {}
    with pytest.raises(ConfigError):
        instagram.reel(Ctx(cfg), item())
