"""autopilot: init, add, status, plan, run, report, doctor, youtube-auth."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from . import __version__, report as rep, schedule
from .config import Config
from .errors import AutopilotError
from .queue import KINDS, load_queue
from .state import Ledger

EXAMPLE_CONFIG = """\
# channel-autopilot config. Never commit this file: it holds your tokens.
name: My channel
timezone: UTC
queue: queue                 # folder of items
state: state.db              # the ledger

# Daily limits per action (these are the defaults; delete what you do not use)
limits:
  youtube.short: 2
  youtube.video: 2
  instagram.reel: 1
  instagram.story: 1
  instagram.image: 1
  facebook.reel: 1
  facebook.story: 1
  facebook.image: 1
  facebook.post: 1

youtube:
  client_secret: secrets/youtube-oauth-client.json
  token: secrets/youtube-token.json
  privacy: public
  reset_hour: 8              # YouTube's daily upload cap resets at 08:00 UTC

instagram:
  account_id: "${IG_ACCOUNT_ID}"
  token: "${META_TOKEN}"

facebook:
  page_id: "${FB_PAGE_ID}"
  token: "${META_TOKEN}"

# Instagram and Facebook fetch media from a public https URL
media:
  s3_bucket: ""
  public_base: ""
  prefix: autopilot/

# The daily report
email:
  method: none               # none | smtp | ses
  to: you@example.com
  from: autopilot@example.com
"""


def _cfg(a) -> Config:
    return Config.load(a.config)


def _ledger_items(cfg):
    return Ledger(cfg.path("state", "state.db")), load_queue(cfg.path("queue", "queue"), cfg.actions_for)


def cmd_init(a):
    p = Path(a.config)
    if p.exists():
        print(f"{p} already exists; not touching it")
    else:
        p.write_text(EXAMPLE_CONFIG)
        print(f"wrote {p}: edit it, then `autopilot doctor`")
    (p.parent / "queue").mkdir(exist_ok=True)
    (p.parent / "secrets").mkdir(exist_ok=True)
    gi = p.parent / ".gitignore"                     # keys and tokens never reach a repository
    lines = gi.read_text().splitlines() if gi.exists() else []
    add = [x for x in ("secrets/", "config.yml", "state.db", "out/", "rotation-days/") if x not in lines]
    if add:
        gi.write_text("\n".join(lines + add) + "\n")


def cmd_add(a):
    cfg = _cfg(a)
    folder = cfg.path("queue", "queue") / a.slug
    folder.mkdir(parents=True, exist_ok=False)
    files = {}
    for key, src in (("video", a.video), ("thumbnail", a.thumbnail), ("image", a.image)):
        if src:
            dst = folder / Path(src).name
            dst.write_bytes(Path(src).read_bytes())
            files[key] = dst.name
    item = {"kind": a.kind, "title": a.title or a.slug, "description": a.description or "", "files": files}
    if a.link:
        item["link"] = a.link
    (folder / "item.yml").write_text(yaml.safe_dump(item, sort_keys=False, allow_unicode=True))
    print(f"added {folder}")


def cmd_status(a):
    cfg = _cfg(a)
    ledger, items = _ledger_items(cfg)
    for it in items:
        marks = " ".join(f"{x}{'✓' if ledger.done(it.slug, x) else '·'}" for x in it.actions)
        print(f"{it.slug:<34} {it.kind:<6} {marks}")
    print(f"\n{len(items)} item(s) in the queue")


def cmd_plan(a):
    cfg = _cfg(a)
    ledger, items = _ledger_items(cfg)
    todo = schedule.due(cfg, ledger, items, only=a.only)
    for it, action in todo:
        print(f"would post  {action:<17} {it.slug}")
    print(f"\n{len(todo)} post(s) due now")


def cmd_run(a):
    cfg = _cfg(a)
    ledger, items = _ledger_items(cfg)
    res = schedule.run(cfg, ledger, items, dry_run=a.dry_run, only=a.only)
    for o in res.outcomes:
        print(f"{o.status:<8} {o.action:<17} {o.item}  {o.url or o.error}")
    print(f"\n{len(res.ok())} posted, {len(res.failed())} failed")
    if a.report and not a.dry_run:
        _report(cfg, ledger, items, send=True)
    return 1 if res.failed() else 0


def _report(cfg, ledger, items, send, day=None):
    day = day or schedule.day_key(cfg, "report", datetime.now(timezone.utc))   # "report" has no cap reset: the plain local day
    subject, text, html = rep.build(cfg, ledger, items, day)
    print(text)
    if send:
        print("\n" + rep.send(cfg, subject, text, html))


def cmd_report(a):
    cfg = _cfg(a)
    ledger, items = _ledger_items(cfg)
    _report(cfg, ledger, items, a.send, a.day)


def cmd_make(a):
    from .maker import build, voice
    if a.setup:
        print("voice models in", voice.setup())
        return 0
    if not a.spec:
        raise AutopilotError("give a video.yml (see examples/videos/)")
    cfg_out = Path(a.out)
    res = build.make(a.spec, cfg_out, still_at=a.still, no_render=a.no_render, check_only=a.check, workers=a.workers)
    if a.queue and "video" in res:
        qdir = _cfg(a).path("queue", "queue")
        print("queued:", build.to_queue(res["spec"], res, qdir))
    return 0


def cmd_make_image(a):
    from .maker import image
    png = image.make(a.slug, a.headline, Path(a.out), sub=a.sub or "", kicker=a.kicker or "", footer=a.footer or "",
                     footer_right=a.footer_right or "", preset=a.preset, size=a.size, logo=a.logo)
    print("image:", png)
    if a.queue:
        print("queued:", image.to_queue(a.slug, png, _cfg(a).path("queue", "queue"), a.caption or a.headline.replace("*", "")))
    return 0


def cmd_doctor(a):
    cfg = _cfg(a)
    bad = 0
    for k in ("instagram.account_id", "instagram.token", "facebook.page_id", "facebook.token"):
        v = cfg.get(k)
        print(f"{'ok ' if v else 'MISSING'}  {k}")
        bad += not v
    print(f"{'ok ' if cfg.path('youtube.token', 'secrets/youtube-token.json').exists() else 'MISSING'}  youtube token (run `autopilot youtube-auth`)")
    m = cfg.get("media", {}) or {}
    print(f"{'ok ' if (m.get('command') or (m.get('s3_bucket') and m.get('public_base'))) else 'MISSING'}  media hosting for Instagram/Facebook")
    return 1 if bad else 0


def cmd_youtube_auth(a):
    from .platforms import youtube
    print("token saved:", youtube.auth(_cfg(a)))


def cmd_research(a):
    from . import research
    cfg = _cfg(a)
    seeds = [x.strip() for x in a.seed.split(",")] if a.seed else None
    res = research.run(cfg, seeds=seeds, min_searches=a.min_searches, max_searches=a.max_searches, competition=a.competition,
                       min_bid=a.min_bid, min_words=a.min_words, questions=a.questions or None,
                       keep_navigational=a.keep_navigational or None)
    print(f"{res['ideas']:,} ideas, {res['merged']:,} after merging misspellings, {len(res['rows']):,} passed {res['filters']}")
    for r in res["rows"][:a.limit]:
        print(f"{r['searches']:>10,}  {r['competition']:<7} ${r['bid_low']}-{r['bid_high']:<8} {r['keyword']}")
    if a.csv:
        research.write_csv(res["rows"], Path(a.csv)); print("csv:", a.csv)
    return 0


def cmd_rotation(a):
    import datetime as dt
    from .rotation import Rotation
    rot = Rotation(a.file)
    day = dt.date.fromisoformat(a.date) if a.date else dt.date.today()
    if a.action == "status":
        for i in range(-2, 2 * len(rot.channels)):
            d = day + dt.timedelta(days=i)
            st = rot.state(d)
            done = sum(1 for v in st.get("videos", []) if v.get("queued"))
            print(d, rot.channel_for(d).name, f"{done} queued" if st else "")
        return 0
    st = rot.run(day, publish=a.publish, dry=(a.action == "plan"))
    print(json.dumps(st, indent=1, ensure_ascii=False))
    return 0 if all(not v.get("failed") for v in st.get("videos", [])) else 1


def main(argv=None):
    p = argparse.ArgumentParser(prog="autopilot", description=__doc__)
    p.add_argument("--config", default="config.yml")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init").set_defaults(fn=cmd_init)
    ad = sub.add_parser("add")
    ad.add_argument("slug"); ad.add_argument("--kind", choices=KINDS, required=True)
    ad.add_argument("--title"); ad.add_argument("--description"); ad.add_argument("--video"); ad.add_argument("--thumbnail")
    ad.add_argument("--image"); ad.add_argument("--link")
    ad.set_defaults(fn=cmd_add)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    pl = sub.add_parser("plan"); pl.add_argument("--only"); pl.set_defaults(fn=cmd_plan)
    r = sub.add_parser("run")
    r.add_argument("--dry-run", action="store_true"); r.add_argument("--only"); r.add_argument("--report", action="store_true", help="email the report afterwards")
    r.set_defaults(fn=cmd_run)
    rp = sub.add_parser("report"); rp.add_argument("--send", action="store_true"); rp.add_argument("--day"); rp.set_defaults(fn=cmd_report)
    mk = sub.add_parser("make", help="make a narrated video from a video.yml")
    mk.add_argument("spec", nargs="?"); mk.add_argument("--out", default="out"); mk.add_argument("--setup", action="store_true", help="download the voice models")
    mk.add_argument("--still", type=float, help="write only the thumbnail at this time (seconds) to check the look")
    mk.add_argument("--no-render", action="store_true"); mk.add_argument("--check", action="store_true", help="voice + layout check only")
    mk.add_argument("--queue", action="store_true", help="add the finished video to the publishing queue")
    mk.add_argument("--workers", type=int, default=3); mk.set_defaults(fn=cmd_make)
    mi = sub.add_parser("make-image", help="make a feed image (headline card) for Instagram and Facebook")
    mi.add_argument("slug"); mi.add_argument("--headline", required=True); mi.add_argument("--sub"); mi.add_argument("--kicker")
    mi.add_argument("--footer"); mi.add_argument("--footer-right"); mi.add_argument("--caption"); mi.add_argument("--out", default="out")
    mi.add_argument("--preset", default="calm", choices=["calm", "bold", "light"]); mi.add_argument("--size", default="portrait", choices=["portrait", "square"])
    mi.add_argument("--logo", help="a logo image shown top-left"); mi.add_argument("--queue", action="store_true"); mi.set_defaults(fn=cmd_make_image)
    rs = sub.add_parser("research", help="keyword research with Google Ads Keyword Planner (config: research:)")
    rs.add_argument("--seed", help="comma-separated topics instead of the config's seeds")
    rs.add_argument("--min-searches", type=int); rs.add_argument("--max-searches", type=int); rs.add_argument("--competition")
    rs.add_argument("--min-bid", type=float); rs.add_argument("--min-words", type=int); rs.add_argument("--questions", action="store_true")
    rs.add_argument("--keep-navigational", action="store_true"); rs.add_argument("--limit", type=int, default=30); rs.add_argument("--csv")
    rs.set_defaults(fn=cmd_research)
    ro = sub.add_parser("rotation", help="several channels, one a day: research, write, make, queue (rotation.yml)")
    ro.add_argument("action", choices=["status", "plan", "run"]); ro.add_argument("--file", default="rotation.yml")
    ro.add_argument("--date"); ro.add_argument("--publish", action="store_true", help="run the day's channel publisher afterwards")
    ro.set_defaults(fn=cmd_rotation)
    sub.add_parser("doctor").set_defaults(fn=cmd_doctor)
    sub.add_parser("youtube-auth").set_defaults(fn=cmd_youtube_auth)
    a = p.parse_args(argv)
    try:
        return a.fn(a) or 0
    except AutopilotError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
