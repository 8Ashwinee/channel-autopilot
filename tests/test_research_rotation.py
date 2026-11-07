import datetime as dt
import json
from pathlib import Path

import yaml

from autopilot import cli, research
from autopilot.queue import load_item
from autopilot.rotation import Rotation


def row(k, s, comp="LOW", lo=1.0, hi=5.0, ci=10, rank=0):
    return {"keyword": k, "searches": s, "competition": comp, "competition_index": ci, "bid_low": lo, "bid_high": hi, "rank": rank}


def test_merge_misspellings_keeps_the_clean_most_relevant_form():
    rows = [row("personal loan", 550000, rank=0), row("p loan", 550000, rank=5), row("personalized loans", 550000, rank=9),
            row("persona1 loan", 550000, rank=1), row("debt consolidation", 165000, rank=2)]
    kept = sorted(r["keyword"] for r in research.merge_misspellings(rows))
    assert kept == ["debt consolidation", "personal loan"]


def test_select_filters_navigational_tickers_and_ranks_by_searches_times_bid():
    rows = [row("gmail login", 2_000_000), row("tesla stock", 3_000_000), row("best balance transfer cards", 49500, "MEDIUM", hi=43.0),
            row("how to pay off credit card debt", 40000, hi=20.0), row("credit card", 1_000_000, "HIGH", hi=25.0),
            row("cheap loans", 90000, hi=0.5)]
    out = research.select(rows, min_searches=10000, competition="LOW,MEDIUM", min_bid=1, min_words=3)
    assert [r["keyword"] for r in out] == ["best balance transfer cards", "how to pay off credit card debt"]
    assert out[0]["score"] == round(49500 * 43.0)


def test_select_questions_and_skip():
    rows = [row("how to budget money", 20000), row("budget planner app ideas", 30000)]
    assert [r["keyword"] for r in research.select(rows, min_words=2, questions=True)] == ["how to budget money"]
    assert research.select(rows, min_words=2, skip={"how to budget money", "budget planner app ideas"}) == []


def test_queue_item_carries_publish_at_and_comment(tmp_path):
    d = tmp_path / "x"; d.mkdir(); (d / "v.mp4").write_bytes(b"0")
    (d / "item.yml").write_text(yaml.safe_dump({"kind": "video", "title": "t", "files": {"video": "v.mp4"},
                                                 "publish_at": "2026-11-10T17:30:00Z", "comment": "Which one?"}))
    it = load_item(d, {"video": ["youtube.video"]})
    assert it.publish_at == "2026-11-10T17:30:00Z" and it.comment == "Which one?"


def rot(tmp_path, **extra):
    for c in ("a", "b", "c"):
        (tmp_path / c).mkdir()
    d = {"start_date": "2026-01-05", "channels": ["a", "b", "c"], "per_day": {"short": 1, "video": 2},
         "release": {"time": "12:30", "timezone": "America/New_York", "offsets_days": {"short": [0], "video": [2, 4]}}, **extra}
    (tmp_path / "rotation.yml").write_text(yaml.safe_dump(d))
    return Rotation(tmp_path / "rotation.yml")


def test_rotation_picks_one_channel_a_day_in_order(tmp_path):
    r = rot(tmp_path)
    days = [r.channel_for(dt.date(2026, 1, 5) + dt.timedelta(days=i)).name for i in range(7)]
    assert days == ["a", "b", "c", "a", "b", "c", "a"]
    assert r.slots() == [("short", 0), ("video", 0), ("video", 1)]


def test_release_times_short_same_day_long_videos_plus_2_and_4(tmp_path):
    r = rot(tmp_path)
    now = dt.datetime(2026, 1, 5, 9, 0, tzinfo=dt.timezone.utc)          # 04:00 in New York: today's 12:30 is ahead
    w = r.release_times(now)
    assert w[("short", 0)] == dt.datetime(2026, 1, 5, 17, 30, tzinfo=dt.timezone.utc)
    assert w[("video", 0)] == dt.datetime(2026, 1, 7, 17, 30, tzinfo=dt.timezone.utc)
    assert w[("video", 1)] == dt.datetime(2026, 1, 9, 17, 30, tzinfo=dt.timezone.utc)
    late = dt.datetime(2026, 1, 5, 17, 0, tzinfo=dt.timezone.utc)        # 12:00 in New York: less than 90 min left
    assert r.release_times(late)[("short", 0)].day == 6


def test_dashboard_is_optional(tmp_path):
    r = rot(tmp_path)
    assert r._dash("control") is None and r.sync() == {}


def test_rotation_status_json(tmp_path, capsys):
    r = rot(tmp_path)
    r.save(dt.date(2026, 1, 5), {"videos": [{"queued": "q1"}, {"queued": "q2"}, {"failed": True}]})
    rc = cli.main(["rotation", "status", "--file", str(tmp_path / "rotation.yml"), "--date", "2026-01-05", "--json"])
    assert rc == 0
    rows = json.loads(capsys.readouterr().out)
    assert len(rows) == 8
    assert rows[0] == {"date": "2026-01-03", "channel": "b", "queued": 0}
    assert rows[2] == {"date": "2026-01-05", "channel": "a", "queued": 2}
    assert [x["channel"] for x in rows[2:5]] == ["a", "b", "c"]

