from datetime import datetime, timezone

from autopilot import platforms, schedule
from autopilot.config import DEFAULT_ACTIONS, Config
from autopilot.errors import AutopilotError, QuotaReached
from autopilot.platforms import Result
from autopilot.queue import load_queue
from conftest import make_item

NOW = datetime(2026, 11, 6, 10, 0, tzinfo=timezone.utc)


def _items(tmp_path, n):
    q = tmp_path / "q"
    for i in range(n):
        make_item(q, f"s{i}", actions=["youtube.short", "instagram.reel"])
    return load_queue(q, DEFAULT_ACTIONS)


def _fake(monkeypatch, fn):
    monkeypatch.setattr(platforms, "get", lambda action: fn)


def test_respects_daily_limit_and_order(cfg, ledger, tmp_path, monkeypatch):
    _fake(monkeypatch, lambda ctx, it: Result(f"https://x/{it.slug}", it.slug))
    items = _items(tmp_path, 4)
    r = schedule.run(cfg, ledger, items, now=NOW)
    assert [(o.action, o.item) for o in r.ok()] == [("youtube.short", "s0"), ("youtube.short", "s1"), ("instagram.reel", "s0")]


def test_never_posts_twice(cfg, ledger, tmp_path, monkeypatch):
    calls = []
    _fake(monkeypatch, lambda ctx, it: (calls.append(it.slug), Result("https://x"))[1])
    items = _items(tmp_path, 1)
    schedule.run(cfg, ledger, items, now=NOW)
    schedule.run(cfg, ledger, items, now=NOW)
    assert calls == ["s0", "s0"]   # once for youtube.short, once for instagram.reel; the second run posts nothing


def test_next_day_continues_the_queue(cfg, ledger, tmp_path, monkeypatch):
    _fake(monkeypatch, lambda ctx, it: Result("https://x"))
    items = _items(tmp_path, 4)
    schedule.run(cfg, ledger, items, now=NOW)
    day2 = datetime(2026, 11, 7, 10, 0, tzinfo=timezone.utc)
    r = schedule.run(cfg, ledger, items, now=day2)
    assert [(o.action, o.item) for o in r.ok()] == [("youtube.short", "s2"), ("youtube.short", "s3"), ("instagram.reel", "s1")]


def test_quota_stops_the_action_without_a_failure(cfg, ledger, tmp_path, monkeypatch):
    def boom(ctx, it): raise QuotaReached("cap")
    _fake(monkeypatch, boom)
    r = schedule.run(cfg, ledger, _items(tmp_path, 3), now=NOW, only="youtube.short")
    assert [o.status for o in r.outcomes] == ["quota"]       # stopped at the first one
    assert ledger.failures("s0", "youtube.short") == 0        # and not counted against the item


def test_failure_is_recorded_retried_then_given_up(cfg, ledger, tmp_path, monkeypatch):
    def bad(ctx, it): raise AutopilotError("nope")
    _fake(monkeypatch, bad)
    items = _items(tmp_path, 1)
    for d in (6, 7, 8, 9):
        schedule.run(cfg, ledger, items, now=datetime(2026, 11, d, 10, tzinfo=timezone.utc), only="instagram.reel")
    assert ledger.failures("s0", "instagram.reel") == 3        # max_attempts, then it stops trying


def test_one_failure_does_not_stop_the_rest(cfg, ledger, tmp_path, monkeypatch):
    def flaky(ctx, it):
        if it.slug == "s0": raise AutopilotError("bad file")
        return Result("https://x")
    _fake(monkeypatch, flaky)
    r = schedule.run(cfg, ledger, _items(tmp_path, 3), now=NOW, only="youtube.short")
    assert [o.status for o in r.outcomes] == ["failed", "ok"]


def test_dry_run_records_nothing(cfg, ledger, tmp_path):
    r = schedule.run(cfg, ledger, _items(tmp_path, 2), dry_run=True, now=NOW)
    assert r.outcomes and all(o.status == "dry-run" for o in r.outcomes) and not ledger.rows()


def test_day_resets_at_the_platform_hour():
    c = Config({"timezone": "UTC", "youtube": {"reset_hour": 8}}, None)
    assert schedule.day_key(c, "youtube.short", datetime(2026, 11, 6, 7, 59, tzinfo=timezone.utc)) == "2026-11-05"
    assert schedule.day_key(c, "youtube.short", datetime(2026, 11, 6, 8, 0, tzinfo=timezone.utc)) == "2026-11-06"
    assert schedule.day_key(c, "instagram.reel", datetime(2026, 11, 6, 7, 59, tzinfo=timezone.utc)) == "2026-11-06"
