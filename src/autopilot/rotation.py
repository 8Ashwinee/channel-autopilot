"""The rotation: several channels, one channel a day, a fixed set of videos per day, researched, written, made and queued.

A rotation is a folder with a rotation.yml; each channel is an ordinary autopilot folder (its own config.yml with its own
YouTube sign-in, research block and `brief:`, its own queue and ledger). Run it daily (cron / launchd):

  autopilot rotation status   [--file rotation.yml]     which channel on which day, what ran
  autopilot rotation plan     [--file ...] [--date D]   today's channel and the topics research would pick (makes nothing)
  autopilot rotation run      [--file ...] [--date D] [--publish]

rotation.yml:
  start_date: 2026-01-05          # day 0 of the cycle
  channels: [../tech-channel, ../money-channel]   # folders with a config.yml each; one per day in this order
  per_day: {short: 1, video: 2}   # what to make for the day's channel
  release:                        # scheduled publishing: uploaded on the day, public at these times
    time: "12:30"
    timezone: America/New_York
    offsets_days: {short: [0], video: [2, 4]}
  writer:                         # any command that writes a video.yml for `autopilot make` (see examples/rotation/)
    command: [claude, -p, "{prompt}", --dangerously-skip-permissions, --allowedTools, "Read Write Edit WebFetch WebSearch", --max-turns, "120"]
    prompt_file: writer.md        # a template: {channel} {brief} {kind} {keyword} {searches} {bid} {spec} {date} {length}
  lengths: {short: "35 to 55 seconds of speech", video: "8 to 10 minutes of speech"}
  dashboard: {url: "", token_file: ""}   # optional: report each day to a dashboard (see dashboard/)

What a day does: research (the channel's `research:` block, topics it never used) → for each slot, the writer command
writes <channel>/videos/<date>/<slug>.yml → `autopilot make` renders it → it is queued with `publish_at` → the topic is
recorded as used. With --publish the channel's `autopilot run` posts what is due (its daily limits still apply).
Everything is idempotent per day: a second run continues where the first stopped.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import subprocess
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from .config import Config
from .errors import ConfigError


class Rotation:
    def __init__(self, path: str | Path):
        self.file = Path(path).expanduser().resolve()
        if not self.file.exists():
            raise ConfigError(f"no rotation file at {self.file}")
        self.base = self.file.parent
        self.d = yaml.safe_load(self.file.read_text()) or {}
        self.channels = [(self.base / c).resolve() for c in self.d.get("channels", [])]
        if not self.channels:
            raise ConfigError("rotation.yml: channels is empty")
        self.start = dt.date.fromisoformat(str(self.d.get("start_date", dt.date.today())))
        self.days_dir = self.base / "rotation-days"

    def channel_for(self, day: dt.date) -> Path:
        return self.channels[(day - self.start).days % len(self.channels)]

    def slots(self) -> list[tuple[str, int]]:
        """[("short", 0), ("video", 0), ("video", 1)] for per_day {short: 1, video: 2}."""
        per = self.d.get("per_day") or {"short": 1, "video": 2}
        return [(kind, i) for kind in ("short", "video") for i in range(int(per.get(kind, 0)))]

    def release_times(self, now_utc: dt.datetime) -> dict:
        """UTC go-live time per slot: the next release time at least 90 minutes away, plus the slot's offset in days."""
        r = self.d.get("release") or {}
        tz = ZoneInfo(r.get("timezone", "America/New_York"))
        hh, mm = map(int, str(r.get("time", "12:30")).split(":"))
        local = now_utc.astimezone(tz)
        base = dt.datetime(local.year, local.month, local.day, hh, mm, tzinfo=tz)
        if base - now_utc < dt.timedelta(minutes=90):
            base += dt.timedelta(days=1)
        offs = (r.get("offsets_days") or {"short": [0], "video": [2, 4]})
        out = {}
        for kind, i in self.slots():
            lst = offs.get(kind) or [0]
            out[(kind, i)] = (base + dt.timedelta(days=int(lst[min(i, len(lst) - 1)]))).astimezone(dt.timezone.utc)
        return out

    # -------------------------------------------------------------- state
    def state(self, day):
        p = self.days_dir / f"{day.isoformat()}.json"
        return json.loads(p.read_text()) if p.exists() else {}

    def save(self, day, st):
        self.days_dir.mkdir(parents=True, exist_ok=True)
        (self.days_dir / f"{day.isoformat()}.json").write_text(json.dumps(st, indent=1, ensure_ascii=False))

    # -------------------------------------------------------------- dashboard (optional; channel ids = folder names)
    def _dash(self, path, body=None):
        dash = self.d.get("dashboard") or {}
        if not dash.get("url") or not dash.get("token_file"):
            return None
        try:
            tok = Path(dash["token_file"]).expanduser().read_text().strip()
            h, data = {"x-svc-token": tok}, None
            if body is not None:
                data = json.dumps(body, ensure_ascii=False).encode()
                h.update({"Content-Type": "application/json", "x-amz-content-sha256": hashlib.sha256(data).hexdigest()})
            req = urllib.request.Request(dash["url"].rstrip("/") + "/api/svc/" + path, data=data, headers=h,
                                         method="POST" if data is not None else "GET")
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read() or b"{}")
        except Exception as e:  # a dashboard problem never stops the day
            print("dashboard:", path, str(e)[:150])
            return None

    def report(self, st):
        self._dash("rotation", {**st, "channel": Path(st.get("folder", "")).name or st.get("channel"),
                                "updated": dt.datetime.now(dt.timezone.utc).isoformat()})

    def sync(self):
        """Tell the dashboard the order, the start date and each channel's seeds; read back pause + topic choices."""
        seeds = {}
        for c in self.channels:
            try:
                r = (Config.load(c / "config.yml").get("research") or {})
                seeds[c.name] = {"seeds": r.get("seeds", []), "filters": r.get("filters", {})}
            except Exception:
                pass
        self._dash("sync", {"order": [c.name for c in self.channels], "start_date": self.start.isoformat(), "seeds": seeds})
        return self._dash("control") or {}

    # -------------------------------------------------------------- the day
    def topics(self, cfg: Config, n: int, pins=(), bans=()) -> list[dict]:
        """The best n topics the channel never used; dashboard "Use next" topics first, "Never" topics never."""
        from . import research
        rows = research.run(cfg)["rows"]
        bans = {b.lower() for b in bans}
        by = {r["keyword"].lower(): r for r in rows}
        picked = [by.get(p.lower(), {"keyword": p, "searches": 0, "competition": "UNKNOWN", "bid_low": 0, "bid_high": 0})
                  for p in pins if p.lower() not in bans and p.lower() not in research.used(cfg)]
        seen = {p["keyword"].lower() for p in picked}
        picked += [r for r in rows if r["keyword"].lower() not in bans and r["keyword"].lower() not in seen]
        return picked[:n]

    def write(self, cfg, ch: Path, day, kind, topic, spec: Path) -> bool:
        w = self.d.get("writer") or {}
        if not w.get("command"):
            raise ConfigError("rotation.yml: writer.command is missing")
        tmpl = (self.base / w.get("prompt_file", "writer.md")).read_text()
        lengths = self.d.get("lengths") or {"short": "35 to 55 seconds of speech", "video": "8 to 10 minutes of speech"}
        prompt = tmpl.format(channel=cfg.get("name", ch.name), brief=cfg.get("brief", ""), kind=kind, keyword=topic["keyword"],
                             searches=topic.get("searches", 0), bid=topic.get("bid_high", 0), spec=str(spec), date=day.isoformat(),
                             length=lengths.get(kind, ""))
        cmd = [c.replace("{prompt}", prompt) for c in w["command"]]
        spec.parent.mkdir(parents=True, exist_ok=True)
        with open(spec.with_suffix(".writer.log"), "w") as fh:
            subprocess.run(cmd, cwd=ch, stdout=fh, stderr=subprocess.STDOUT, timeout=int(w.get("timeout", 3600)))
        return spec.exists()

    def run(self, day: dt.date, publish=False, dry=False) -> dict:
        from . import research
        from .maker import build
        ch = self.channel_for(day)
        cfg = Config.load(ch / "config.yml")
        ctrl = self.sync()
        if ctrl.get("enabled") is False:
            return {"date": day.isoformat(), "paused": True}
        st = self.state(day) or {"date": day.isoformat(), "channel": cfg.get("name", ch.name), "folder": str(ch), "videos": []}
        if not st.get("topics"):
            st["topics"] = self.topics(cfg, len(self.slots()), (ctrl.get("pins") or {}).get(ch.name, []),
                                       (ctrl.get("bans") or {}).get(ch.name, []))
            self.save(day, st)
        if dry:
            return st
        when = self.release_times(dt.datetime.now(dt.timezone.utc))
        done = {(v["kind"], v["i"]) for v in st["videos"] if v.get("queued") or v.get("failed")}
        for (kind, i), topic in zip(self.slots(), st["topics"]):
            if (kind, i) in done:
                continue
            slug = re.sub(r"[^a-z0-9]+", "-", topic["keyword"].lower()).strip("-")[:48] + f"-{day.strftime('%m%d')}"
            spec = ch / "videos" / day.isoformat() / f"{slug}.yml"
            v = {"kind": kind, "i": i, "keyword": topic["keyword"], "spec": str(spec)}
            try:
                if not spec.exists() and not self.write(cfg, ch, day, kind, topic, spec):
                    raise RuntimeError("the writer wrote no video.yml")
                res = build.make(str(spec), ch / "out" / "videos")
                sp = res["spec"]
                sp.d["publish_at"] = when[(kind, i)].strftime("%Y-%m-%dT%H:%M:%SZ")
                q = build.to_queue(sp, res, cfg.path("queue", "queue"))
                v.update({"queued": str(q), "title": sp.title, "publish_at": sp.d["publish_at"]})
                research.mark_used(cfg, [topic["keyword"]])
            except Exception as e:
                v.update({"failed": True, "reason": str(e)[:300]})
            st["videos"].append(v)
            self.save(day, st)
            self.report(st)
        if publish:
            p = subprocess.run(["autopilot", "--config", str(ch / "config.yml"), "run", "--report"], cwd=ch, capture_output=True, text=True)
            st["publish_log"] = (p.stdout + p.stderr)[-2000:]
            self.save(day, st)
        self.report(st)
        return st
