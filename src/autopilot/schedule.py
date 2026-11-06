"""The daily runner: for each action, post the next queued items until that action's daily limit is reached."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from . import platforms
from .config import Config
from .errors import QuotaReached
from .queue import Item
from .state import Ledger


def day_key(cfg: Config, action: str, now: datetime | None = None) -> str:
    """The platform's own 'today'. Some caps reset at a fixed hour (YouTube's at 08:00 UTC for example):
    set `reset_hour` under the platform in the config and its day starts then."""
    now = now or datetime.now(timezone.utc)
    tz = ZoneInfo(cfg.get("timezone", "UTC"))
    hour = int(cfg.get(f"{action.split('.')[0]}.reset_hour", 0) or 0)
    return (now.astimezone(tz) - timedelta(hours=hour)).date().isoformat()


@dataclass
class Ctx:
    cfg: Config


@dataclass
class Outcome:
    item: str
    action: str
    status: str            # ok | failed | dry-run | quota
    url: str = ""
    error: str = ""


@dataclass
class RunResult:
    outcomes: list = field(default_factory=list)

    def ok(self):
        return [o for o in self.outcomes if o.status == "ok"]

    def failed(self):
        return [o for o in self.outcomes if o.status == "failed"]


def due(cfg: Config, ledger: Ledger, items: list[Item], now=None, only: str | None = None) -> list[tuple[Item, str]]:
    """What would run now: (item, action) pairs in queue order, within each action's remaining daily allowance."""
    max_attempts = int(cfg.get("max_attempts", 3))
    out, taken = [], {}
    for action, limit in cfg.limits.items():
        if only and action != only:
            continue
        day = day_key(cfg, action, now)
        room = int(limit) - ledger.count(action, day)
        for it in items:
            if room <= 0:
                break
            if action not in it.actions or ledger.done(it.slug, action) or ledger.failures(it.slug, action) >= max_attempts:
                continue
            out.append((it, action))
            room -= 1
    return out


def run(cfg: Config, ledger: Ledger, items: list[Item], dry_run=False, now=None, only: str | None = None) -> RunResult:
    res, ctx, stopped = RunResult(), Ctx(cfg), set()
    for it, action in due(cfg, ledger, items, now, only):
        if action in stopped:
            continue
        if dry_run:
            res.outcomes.append(Outcome(it.slug, action, "dry-run"))
            continue
        day = day_key(cfg, action, now)
        try:
            r = platforms.get(action)(ctx, it)
            ledger.record_ok(it.slug, action, day, r.url, r.remote_id)
            res.outcomes.append(Outcome(it.slug, action, "ok", r.url))
        except QuotaReached as e:
            stopped.add(action)   # the platform said stop for today: leave the item for tomorrow, not a failure
            res.outcomes.append(Outcome(it.slug, action, "quota", error=str(e)))
        except Exception as e:     # one bad post must not stop the rest of the day
            ledger.record_failed(it.slug, action, day, e)
            res.outcomes.append(Outcome(it.slug, action, "failed", error=str(e)))
    return res
