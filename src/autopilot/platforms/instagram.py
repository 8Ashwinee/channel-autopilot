"""Instagram (Graph API, Instagram business account linked to a Facebook Page).

config:
  instagram:
    account_id: "1784..."          # the Instagram business account id
    token: ${META_TOKEN}           # system-user or long-lived token with instagram_content_publish
    api_version: v21.0             # optional
Media is fetched by Instagram from a public https URL; see media.py.
"""
from __future__ import annotations

import time

from .. import http, media
from ..errors import AutopilotError, ConfigError, QuotaReached
from . import Result


def _cfg(ctx):
    c = ctx.cfg.get("instagram", {}) or {}
    if not c.get("account_id") or not c.get("token"):
        raise ConfigError("instagram.account_id and instagram.token are required")
    return c["account_id"], c["token"], f"https://graph.facebook.com/{c.get('api_version', 'v21.0')}/"


def _call(api, token, path, method="GET", **q):
    q["access_token"] = token
    try:
        return http.request(method, api + path, q)
    except AutopilotError as e:
        if "content_publishing_limit" in str(e) or "(#4)" in str(e) or "rate limit" in str(e).lower():
            raise QuotaReached(str(e)) from None
        raise


def _publish(api, token, ig, container, wait=300, poll=5):
    deadline = time.time() + wait
    while True:
        s = _call(api, token, container, fields="status_code,status")
        if s.get("status_code") == "FINISHED":
            break
        if s.get("status_code") in ("ERROR", "EXPIRED"):
            raise AutopilotError(f"Instagram container {s.get('status_code')}: {s.get('status')}")
        if time.time() > deadline:
            raise AutopilotError("Instagram container still processing after %ss" % wait)
        time.sleep(poll)
    pub = _call(api, token, f"{ig}/media_publish", "POST", creation_id=container)
    link = _call(api, token, pub["id"], fields="permalink").get("permalink", "")
    return Result(url=link or f"https://www.instagram.com/ (media {pub['id']})", remote_id=pub["id"])


def reel(ctx, item):
    ig, tok, api = _cfg(ctx)
    q = dict(media_type="REELS", video_url=media.host(ctx.cfg, item.files["video"], item.slug),
             caption=item.text(), share_to_feed="true")
    if item.files.get("thumbnail"):
        q["cover_url"] = media.host(ctx.cfg, item.files["thumbnail"], item.slug)
    return _publish(api, tok, ig, _call(api, tok, f"{ig}/media", "POST", **q)["id"])


def image(ctx, item):
    ig, tok, api = _cfg(ctx)
    c = _call(api, tok, f"{ig}/media", "POST", image_url=media.host(ctx.cfg, item.files["image"], item.slug), caption=item.text())
    return _publish(api, tok, ig, c["id"])


def story(ctx, item):
    """A 24-hour story from the item's video (or its image). Stories carry no caption."""
    ig, tok, api = _cfg(ctx)
    if item.files.get("video"):
        q = dict(media_type="STORIES", video_url=media.host(ctx.cfg, item.files["video"], item.slug))
    else:
        q = dict(media_type="STORIES", image_url=media.host(ctx.cfg, item.files["image"], item.slug))
    return _publish(api, tok, ig, _call(api, tok, f"{ig}/media", "POST", **q)["id"])
