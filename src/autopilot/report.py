"""The daily report: every live URL posted today, what failed, what is queued next. Text + HTML."""
from __future__ import annotations

import html
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json
import smtplib
import subprocess
from email.message import EmailMessage

from .config import Config
from .errors import ConfigError
from .state import Ledger


def build(cfg: Config, ledger: Ledger, items, day: str) -> tuple[str, str, str]:
    """-> (subject, text, html)"""
    # the report covers the local calendar day, by time of posting (the ledger's own `day` follows each platform's cap reset)
    tz = ZoneInfo(cfg.get("timezone", "UTC"))
    start = datetime.fromisoformat(day).replace(tzinfo=tz)
    lo, hi = start.timestamp(), (start + timedelta(days=1)).timestamp()
    rows = [p for p in ledger.rows() if lo <= p.ts < hi]
    ok = [p for p in rows if p.status == "ok"]
    bad = [p for p in rows if p.status == "failed"]
    pending = sum(1 for it in items for a in it.actions if not ledger.done(it.slug, a))
    sched = _schedule_rows(cfg, ledger, items, rows)
    name = cfg.get("name", "Channel autopilot")
    subject = f"{name}: {len(ok)} posted, {len(bad)} failed ({day})"
    t = [f"{name} — daily report for {day}", "", f"Posted today: {len(ok)}"]
    t += [f"  {p.action:<17} {p.item}\n    {p.url}" for p in ok] or ["  nothing posted"]
    if bad:
        t += ["", f"Failed today: {len(bad)}"] + [f"  {p.action:<17} {p.item}: {p.error}" for p in bad]
    t += ["", "Schedule for the day (posted / daily limit):"] + [f"  {mark} {a:<17} {n}/{lim}  {note}".rstrip() for mark, a, n, lim, note in sched]
    t += ["", f"Still queued: {pending} post(s) across {len(items)} item(s)"]
    rows = "".join(f"<tr><td>{html.escape(p.action)}</td><td>{html.escape(p.item)}</td><td><a href='{html.escape(p.url or '')}'>{html.escape(p.url or '')}</a></td></tr>" for p in ok) \
        or "<tr><td colspan=3>nothing posted</td></tr>"
    fails = "".join(f"<li>{html.escape(p.action)} {html.escape(p.item)}: {html.escape(p.error or '')}</li>" for p in bad)
    h = (f"<h2>{html.escape(name)} — {day}</h2><p>Posted today: <b>{len(ok)}</b></p>"
         f"<table cellpadding=6 border=1 style='border-collapse:collapse'><tr><th>Action</th><th>Item</th><th>Live URL</th></tr>{rows}</table>"
         + (f"<h3>Failed ({len(bad)})</h3><ul>{fails}</ul>" if bad else "")
         + "<h3>Schedule for the day</h3><table cellpadding=6 border=1 style='border-collapse:collapse'><tr><th></th><th>Action</th><th>Posted / limit</th><th>Note</th></tr>"
         + "".join(f"<tr><td>{m}</td><td>{html.escape(a)}</td><td>{n}/{lim}</td><td>{html.escape(note)}</td></tr>" for m, a, n, lim, note in sched) + "</table>"
         + f"<p>Still queued: {pending} post(s) across {len(items)} item(s).</p>")
    return subject, "\n".join(t), h


def _schedule_rows(cfg, ledger, items, rows):
    """One row per action in the schedule: did it reach its daily limit, and if not, why."""
    out = []
    for action, lim in cfg.limits.items():
        n = sum(1 for p in rows if p.status == "ok" and p.action == action)
        failed = sum(1 for p in rows if p.status == "failed" and p.action == action)
        waiting = any(action in it.actions and not ledger.done(it.slug, action) for it in items)
        if n >= int(lim):
            out.append(("✓", action, n, lim, ""))
        elif failed:
            out.append(("✗", action, n, lim, f"{failed} failed (see above)"))
        elif waiting:
            out.append(("…", action, n, lim, "queued, not posted yet (platform cap or retry pending)"))
        else:
            out.append(("✗", action, n, lim, "nothing queued"))
    return out


def send(cfg: Config, subject: str, text: str, body_html: str):
    e = cfg.get("email", {}) or {}
    method, to = e.get("method", "none"), e.get("to")
    if method == "none":
        return "not sent (email.method is none)"
    if not to or not e.get("from"):
        raise ConfigError("email.to and email.from are required")
    if method == "smtp":
        m = EmailMessage()
        m["Subject"], m["From"], m["To"] = subject, e["from"], to
        m.set_content(text)
        m.add_alternative(body_html, subtype="html")
        with smtplib.SMTP(e["host"], int(e.get("port", 587))) as s:
            s.starttls()
            if e.get("user"):
                s.login(e["user"], e["password"])
            s.send_message(m)
        return f"sent to {to} by SMTP"
    if method == "ses":
        payload = {"FromEmailAddress": e["from"], "Destination": {"ToAddresses": [to]},
                   "Content": {"Simple": {"Subject": {"Data": subject}, "Body": {"Text": {"Data": text}, "Html": {"Data": body_html}}}}}
        cmd = ["aws", "sesv2", "send-email", "--cli-input-json", json.dumps(payload)]
        if e.get("region"):
            cmd += ["--region", e["region"]]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode:
            raise ConfigError(f"SES send failed: {r.stderr.strip()[:300]}")
        return f"sent to {to} by SES"
    raise ConfigError(f"email.method must be none, smtp or ses, got {method!r}")
