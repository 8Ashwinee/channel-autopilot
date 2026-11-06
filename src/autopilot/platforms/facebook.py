"""Facebook Page (Graph API). The system/user token is exchanged for the Page's own token at run time.

config:
  facebook:
    page_id: "4766..."
    token: ${META_TOKEN}        # needs pages_manage_posts and publish_video
    api_version: v21.0
"""
from __future__ import annotations

import json
import time
import urllib.request

from .. import http, media
from ..errors import AutopilotError, ConfigError
from . import Result


def _cfg(ctx):
    c = ctx.cfg.get("facebook", {}) or {}
    if not c.get("page_id") or not c.get("token"):
        raise ConfigError("facebook.page_id and facebook.token are required")
    return c["page_id"], c["token"], f"https://graph.facebook.com/{c.get('api_version', 'v21.0')}/"


def _page_token(page, tok, api):
    cache = getattr(_page_token, "_c", {})
    if page not in cache:
        cache[page] = http.request("GET", api + page, {"fields": "access_token", "access_token": tok})["access_token"]
        _page_token._c = cache
    return cache[page]


def _wait_ready(api, pt, vid, wait=600, poll=10):
    deadline = time.time() + wait
    while True:
        s = http.request("GET", api + vid, {"fields": "status,permalink_url", "access_token": pt})
        state = (s.get("status") or {}).get("video_status")
        if state == "ready":
            return s
        if state == "error":
            raise AutopilotError(f"Facebook video error: {s.get('status')}")
        if time.time() > deadline:
            raise AutopilotError("Facebook video still processing after %ss" % wait)
        time.sleep(poll)


def _permalink(s):
    p = s.get("permalink_url", "")
    return p if p.startswith("http") else "https://www.facebook.com" + p


def reel(ctx, item):
    page, tok, api = _cfg(ctx)
    pt = _page_token(page, tok, api)
    r = http.request("POST", f"{api}{page}/videos", {"file_url": media.host(ctx.cfg, item.files["video"], item.slug),
                                                      "description": item.text(), "access_token": pt})
    return Result(url=_permalink(_wait_ready(api, pt, r["id"])), remote_id=r["id"])


def story(ctx, item):
    page, tok, api = _cfg(ctx)
    pt = _page_token(page, tok, api)
    st = http.request("POST", f"{api}{page}/video_stories", {"upload_phase": "start", "access_token": pt})
    up = urllib.request.Request(st["upload_url"], method="POST",
                                headers={"Authorization": "OAuth " + pt, "file_url": media.host(ctx.cfg, item.files["video"], item.slug)})
    with urllib.request.urlopen(up, timeout=300) as r:
        if not json.loads(r.read().decode() or "{}").get("success"):
            raise AutopilotError("Facebook story upload was not accepted")
    fin = http.request("POST", f"{api}{page}/video_stories", {"upload_phase": "finish", "video_id": st["video_id"], "access_token": pt})
    _wait_ready(api, pt, st["video_id"])
    return Result(url=f"https://www.facebook.com/{page}", remote_id=str(fin.get("post_id", st["video_id"])))


def image(ctx, item):
    page, tok, api = _cfg(ctx)
    pt = _page_token(page, tok, api)
    r = http.request("POST", f"{api}{page}/photos", {"url": media.host(ctx.cfg, item.files["image"], item.slug),
                                                     "caption": item.text(), "access_token": pt})
    pid = r.get("post_id") or r["id"]
    return Result(url=_permalink(http.request("GET", api + pid, {"fields": "permalink_url", "access_token": pt})), remote_id=pid)


def post(ctx, item):
    page, tok, api = _cfg(ctx)
    pt = _page_token(page, tok, api)
    q = {"message": item.text(), "access_token": pt}
    if item.link:
        q["link"] = item.link
    r = http.request("POST", f"{api}{page}/feed", q)
    return Result(url=_permalink(http.request("GET", api + r["id"], {"fields": "permalink_url", "access_token": pt})), remote_id=r["id"])
