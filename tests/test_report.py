from datetime import datetime, timezone

from autopilot import report, schedule
from autopilot.errors import AutopilotError
from autopilot.platforms import Result
from autopilot import platforms
from autopilot.config import DEFAULT_ACTIONS
from autopilot.queue import load_queue
from conftest import make_item


def test_report_lists_every_live_url_and_failures(cfg, ledger, tmp_path, monkeypatch):
    q = tmp_path / "q"
    make_item(q, "good", actions=["youtube.short"]); make_item(q, "bad", actions=["instagram.reel"])
    items = load_queue(q, DEFAULT_ACTIONS)

    def fn(ctx, it):
        if it.slug == "bad": raise AutopilotError("container ERROR")
        return Result("https://youtube.com/shorts/ABC", "ABC")
    monkeypatch.setattr(platforms, "get", lambda a: fn)
    now = datetime.now(timezone.utc)
    schedule.run(cfg, ledger, items, now=now)
    day = schedule.day_key(cfg, "report", now)
    subject, text, html = report.build(cfg, ledger, items, day)
    assert "1 posted, 1 failed" in subject
    assert "https://youtube.com/shorts/ABC" in text and "https://youtube.com/shorts/ABC" in html
    assert "container ERROR" in text


def test_email_none_does_not_send(cfg):
    assert "not sent" in report.send(cfg, "s", "t", "<p>h</p>")
