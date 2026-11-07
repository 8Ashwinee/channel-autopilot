"""Channel Studio API (<your domain>/api/*) and the daily collector, one Lambda.

Browser calls carry the Cognito ID token in `x-st-token` (CloudFront's OAC owns Authorization) and must belong to an
address in ALLOWED_EMAILS. The rotation (autopilot rotation) calls /api/svc/* with `x-svc-token` (SSM <prefix>/svc_token).
Data lives in the DynamoDB table as JSON strings (no floats in DynamoDB):
  CH#<ch>/SNAP | DAILY | SEARCH | TRAFFIC | TOPVIDEOS | UPLOADS      written by collect()
  GSC/<site>                                                         written by collect()
  ROT/DAY#<date>                                                     pushed by the Mac (rotation/run.py)
  CTRL/MAIN  {enabled, pins{ch:[kw]}, bans{ch:[kw]}, seeds{ch:{seeds,filters}}, order, start_date}
SSM <SSM_PREFIX>/: channels, youtube/<id> (OAuth refresh token JSON), google/sa (service account key), ads/customer_id,
client_id, svc_token. Nothing here is specific to one owner: every key is yours.
"""
import base64, json, os, time, urllib.parse, urllib.request
from datetime import date, datetime, timedelta, timezone

import boto3, jwt

TABLE = boto3.resource("dynamodb").Table(os.environ["TABLE"])
SSM = boto3.client("ssm")
REGION = os.environ.get("AWS_REGION", "us-east-1")
POOL = os.environ["USER_POOL_ID"]   # the app client id is read from SSM <prefix>/client_id (template cycle otherwise)
ALLOWED = {e.strip().lower() for e in os.environ.get("ALLOWED_EMAILS", "").split(",") if e.strip()}
PREFIX = os.environ.get("SSM_PREFIX", "/chstudio")
_cache = {}


def channels():
    """Your channels: SSM <prefix>/channels = [{"id": "tech", "name": "My Tech Channel"}, ...] (dashboard/add_channel.py)."""
    if "channels" not in _cache:
        _cache["channels"] = json.loads(secret("channels"))
    return _cache["channels"]


def CH_IDS():
    return [c["id"] for c in channels()]


def NAME(ch):
    return next((c["name"] for c in channels() if c["id"] == ch), ch)


# ------------------------------------------------------------------ storage
def put(pk, sk, obj):
    TABLE.put_item(Item={"pk": pk, "sk": sk, "data": json.dumps(obj, ensure_ascii=False), "at": datetime.now(timezone.utc).isoformat()})


def get(pk, sk, default=None):
    it = TABLE.get_item(Key={"pk": pk, "sk": sk}).get("Item")
    return json.loads(it["data"]) if it else default


def query(pk, prefix=""):
    from boto3.dynamodb.conditions import Key
    kc = Key("pk").eq(pk) & (Key("sk").begins_with(prefix) if prefix else Key("sk").gt(" "))
    return [(i["sk"], json.loads(i["data"]), i.get("at")) for i in TABLE.query(KeyConditionExpression=kc)["Items"]]


def secret(name):
    if name not in _cache:
        _cache[name] = SSM.get_parameter(Name=f"{PREFIX}/{name}", WithDecryption=True)["Parameter"]["Value"]
    return _cache[name]


# ------------------------------------------------------------------ HTTP helpers
def http(url, data=None, headers=None, method=None, timeout=60):
    body = None if data is None else (data if isinstance(data, bytes) else json.dumps(data).encode())
    h = {"Content-Type": "application/json", **(headers or {})} if data is not None and not isinstance(data, bytes) else (headers or {})
    req = urllib.request.Request(url, data=body, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read() or b"{}")


def google_user_token(ch):
    """Access token from the channel's stored OAuth refresh token (the Mac's youtube.py sign-in)."""
    k = f"tok:{ch}"
    if k in _cache and _cache[k][1] > time.time() + 60:
        return _cache[k][0]
    t = json.loads(secret(f"youtube/{ch}"))
    form = urllib.parse.urlencode({"client_id": t["client_id"], "client_secret": t["client_secret"],
                                   "refresh_token": t["refresh_token"], "grant_type": "refresh_token"}).encode()
    r = http("https://oauth2.googleapis.com/token", form, {"Content-Type": "application/x-www-form-urlencoded"}, "POST")
    _cache[k] = (r["access_token"], time.time() + r.get("expires_in", 3600))
    return r["access_token"]


def google_sa_token(scope):
    """Access token for the service account (Search Console reader, Google Ads user) by the JWT-bearer grant."""
    k = f"sa:{scope}"
    if k in _cache and _cache[k][1] > time.time() + 60:
        return _cache[k][0]
    sa = json.loads(secret("google/sa"))
    now = int(time.time())
    assertion = jwt.encode({"iss": sa["client_email"], "scope": scope, "aud": "https://oauth2.googleapis.com/token",
                            "iat": now, "exp": now + 3600}, sa["private_key"], algorithm="RS256")
    form = urllib.parse.urlencode({"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion}).encode()
    r = http("https://oauth2.googleapis.com/token", form, {"Content-Type": "application/x-www-form-urlencoded"}, "POST")
    _cache[k] = (r["access_token"], now + r.get("expires_in", 3600))
    return r["access_token"]


def yt(ch, path, **params):
    q = urllib.parse.urlencode(params)
    return http(f"https://youtube.googleapis.com/youtube/v3/{path}?{q}", headers={"Authorization": "Bearer " + google_user_token(ch)})


def yta(ch, **params):
    q = urllib.parse.urlencode({"ids": "channel==MINE", **params})
    return http(f"https://youtubeanalytics.googleapis.com/v2/reports?{q}", headers={"Authorization": "Bearer " + google_user_token(ch)})


def rows(rep):
    cols = [h["name"] for h in rep.get("columnHeaders", [])]
    return [dict(zip(cols, r)) for r in rep.get("rows", [])]


# ------------------------------------------------------------------ collection (daily, and on demand)
def collect_channel(ch):
    end = date.today()
    start90, start28 = (end - timedelta(days=90)).isoformat(), (end - timedelta(days=28)).isoformat()
    c = yt(ch, "channels", part="snippet,statistics,status,contentDetails,brandingSettings", mine="true")["items"][0]
    snap = {"id": c["id"], "title": c["snippet"]["title"], "handle": c["snippet"].get("customUrl", ""),
            "thumb": c["snippet"]["thumbnails"].get("default", {}).get("url", ""),
            "subscribers": int(c["statistics"].get("subscriberCount", 0)), "views": int(c["statistics"].get("viewCount", 0)),
            "videos": int(c["statistics"].get("videoCount", 0)),
            "monetized": c["status"].get("isChannelMonetizationEnabled"),
            "banner": c.get("brandingSettings", {}).get("image", {}).get("bannerExternalUrl", "")}
    put(f"CH#{ch}", "SNAP", snap)
    daily = rows(yta(ch, startDate=start90, endDate=end.isoformat(), dimensions="day", sort="day",
                     metrics="views,estimatedMinutesWatched,averageViewDuration,subscribersGained,subscribersLost,likes,comments,shares"))
    put(f"CH#{ch}", "DAILY", daily)
    errs = {}
    for name, kw in {
        "SEARCH": dict(startDate=start28, endDate=end.isoformat(), dimensions="insightTrafficSourceDetail", metrics="views",
                       filters="insightTrafficSourceType==YT_SEARCH", sort="-views", maxResults=25),
        "TRAFFIC": dict(startDate=start28, endDate=end.isoformat(), dimensions="insightTrafficSourceType", metrics="views,estimatedMinutesWatched", sort="-views"),
        "TOPVIDEOS": dict(startDate=start28, endDate=end.isoformat(), dimensions="video", sort="-views", maxResults=25,
                          metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained"),
    }.items():
        try:
            put(f"CH#{ch}", name, rows(yta(ch, **kw)))
        except Exception as e:
            errs[name] = str(e)[:200]
    # recent uploads (incl. scheduled ones) with titles for the top-videos list
    up = c["contentDetails"]["relatedPlaylists"]["uploads"]
    ids = [i["contentDetails"]["videoId"] for i in yt(ch, "playlistItems", part="contentDetails", playlistId=up, maxResults=50).get("items", [])]
    tv = [r["video"] for r in get(f"CH#{ch}", "TOPVIDEOS", []) if r.get("video")]
    want = list(dict.fromkeys(ids + tv))[:50]
    vids = []
    if want:
        for v in yt(ch, "videos", part="snippet,statistics,status,contentDetails", id=",".join(want)).get("items", []):
            vids.append({"id": v["id"], "title": v["snippet"]["title"], "published": v["snippet"].get("publishedAt"),
                         "publishAt": v["status"].get("publishAt"), "privacy": v["status"].get("privacyStatus"),
                         "duration": v["contentDetails"].get("duration"), "views": int(v["statistics"].get("viewCount", 0)),
                         "likes": int(v["statistics"].get("likeCount", 0)), "comments": int(v["statistics"].get("commentCount", 0)),
                         "thumb": v["snippet"]["thumbnails"].get("medium", {}).get("url", "")})
    put(f"CH#{ch}", "UPLOADS", vids)
    return {"ok": True, "errors": errs}


def collect_gsc():
    tok = google_sa_token("https://www.googleapis.com/auth/webmasters.readonly")
    h = {"Authorization": "Bearer " + tok}
    sites = [s["siteUrl"] for s in http("https://www.googleapis.com/webmasters/v3/sites", headers=h).get("siteEntry", [])]
    end, start = date.today() - timedelta(days=2), date.today() - timedelta(days=30)
    out = {}
    for s in sites:
        base = f"https://www.googleapis.com/webmasters/v3/sites/{urllib.parse.quote(s, safe='')}/searchAnalytics/query"
        q = lambda dims, n=25: http(base, {"startDate": start.isoformat(), "endDate": end.isoformat(), "dimensions": dims, "rowLimit": n}, h, "POST").get("rows", [])
        put("GSC", s, {"site": s, "daily": q(["date"], 40), "queries": q(["query"]), "pages": q(["page"]),
                       "countries": q(["country"], 10), "start": start.isoformat(), "end": end.isoformat()})
        out[s] = "ok"
    return out


def collect(which="all"):
    res = {}
    for ch in (CH_IDS() if which == "all" else [which]):
        try:
            res[ch] = collect_channel(ch)
        except Exception as e:
            res[ch] = {"ok": False, "error": str(e)[:300]}
    if which == "all":
        try:
            res["gsc"] = collect_gsc()
        except Exception as e:
            res["gsc"] = {"ok": False, "error": str(e)[:300]}
    put("SYS", "LASTCOLLECT", {"at": datetime.now(timezone.utc).isoformat(), "result": res})
    return res


# ------------------------------------------------------------------ keyword research (Keyword Planner over REST)
import re
NAV = re.compile(r"\b(login|log in|sign in|signin|sign up|www|\.com|com|near me|app download|customer service|phone number|hours|address|"
                 r"stock price|ticker|futures|today|tonight|tomorrow|live score|scores?|standings|schedule|tickets|weather|radar|"
                 r"forecast|official site|website|apk|download|free online|watch online)\b", re.I)
TICKER = re.compile(r"^\S+ stocks?$", re.I)


def keyword_ideas(seeds):
    tok = google_sa_token("https://www.googleapis.com/auth/adwords")
    cid = secret("ads/customer_id")
    out = {}
    for i in range(0, len(seeds), 20):
        body = {"language": "languageConstants/1000", "geoTargetConstants": ["geoTargetConstants/2840"],
                "keywordPlanNetwork": "GOOGLE_SEARCH", "includeAdultKeywords": False,
                "keywordSeed": {"keywords": seeds[i:i + 20]}, "pageSize": 10000}
        d = http(f"https://googleads.googleapis.com/v26/customers/{cid}:generateKeywordIdeas", body,
                 {"Authorization": "Bearer " + tok}, "POST", timeout=55)
        for n, r in enumerate(d.get("results", [])):
            m = r.get("keywordIdeaMetrics", {})
            out.setdefault(r["text"], {"keyword": r["text"], "rank": len(out), "searches": int(m.get("avgMonthlySearches", 0) or 0),
                                       "competition": m.get("competition", "UNSPECIFIED"), "ci": int(m.get("competitionIndex", 0) or 0),
                                       "bid_low": round(int(m.get("lowTopOfPageBidMicros", 0) or 0) / 1e6, 2),
                                       "bid_high": round(int(m.get("highTopOfPageBidMicros", 0) or 0) / 1e6, 2)})
    # merge misspellings: same figures = same cluster; keep the clean, most relevant form
    groups = {}
    for r in out.values():
        groups.setdefault((r["searches"], r["ci"], r["bid_low"], r["bid_high"]), []).append(r)
    kept = []
    for g in groups.values():
        g.sort(key=lambda r: (bool(re.search(r"\d|[^\x00-\x7f]|_", r["keyword"])), r["rank"]))
        kept.append(g[0])
    return len(out), kept


def keywords(params):
    ctrl = get("CTRL", "MAIN", {}) or {}
    ch = params.get("ch", "")
    seed = [s.strip() for s in params.get("seed", "").split(",") if s.strip()]
    seeds = seed or (ctrl.get("seeds", {}).get(ch, {}).get("seeds") or [])
    if not seeds:
        return {"error": "type a topic, or pick a channel whose seeds the rotation has synced"}
    total, rows_ = keyword_ideas(seeds[:60])
    lo, hi = int(params.get("min", 10000)), int(params.get("max", 10**12))
    comp = set((params.get("comp") or "LOW,MEDIUM").upper().split(","))
    minbid, words = float(params.get("minbid", 0)), int(params.get("words", 2))
    nav = params.get("nav") != "1"
    pins = set(k.lower() for k in ctrl.get("pins", {}).get(ch, [])); bans = set(k.lower() for k in ctrl.get("bans", {}).get(ch, []))
    res = []
    for r in rows_:
        k = r["keyword"]
        if not (lo <= r["searches"] <= hi) or r["competition"] not in comp or r["bid_high"] < minbid or len(k.split()) < words:
            continue
        if nav and (NAV.search(k) or TICKER.search(k)):
            continue
        r["score"] = round(r["searches"] * r["bid_high"]); r["state"] = "pinned" if k.lower() in pins else "banned" if k.lower() in bans else ""
        res.append({x: r[x] for x in ("keyword", "searches", "competition", "bid_low", "bid_high", "score", "state")})
    res.sort(key=lambda r: -r["score"])
    return {"ideas": total, "merged": len(rows_), "passed": len(res), "rows": res[:300], "seeds": seeds[:60]}


# ------------------------------------------------------------------ API
def ok(body, code=200):
    return {"statusCode": code, "headers": {"Content-Type": "application/json", "Cache-Control": "no-store"}, "body": json.dumps(body, ensure_ascii=False)}


def user(event):
    tok = (event.get("headers") or {}).get("x-st-token", "")
    if not tok:
        return None
    if "jwks" not in _cache:
        _cache["jwks"] = jwt.PyJWKClient(f"https://cognito-idp.{REGION}.amazonaws.com/{POOL}/.well-known/jwks.json")
    try:
        key = _cache["jwks"].get_signing_key_from_jwt(tok).key
        c = jwt.decode(tok, key, algorithms=["RS256"], audience=secret("client_id"), issuer=f"https://cognito-idp.{REGION}.amazonaws.com/{POOL}")
    except Exception:
        return None
    if c.get("token_use") != "id" or c.get("email", "").lower() not in ALLOWED:
        return None
    return c["email"].lower()


def schedule(ctrl, days=12):
    order, start = ctrl.get("order") or [], ctrl.get("start_date")
    if not order or not start:
        return []
    s = date.fromisoformat(start)
    return [{"date": (date.today() + timedelta(days=i)).isoformat(),
             "channel": order[((date.today() + timedelta(days=i)) - s).days % len(order)]} for i in range(-1, days)]


def summary(ch):
    snap = get(f"CH#{ch}", "SNAP", {}) or {}
    daily = get(f"CH#{ch}", "DAILY", []) or []
    def s(rows_, k): return sum(int(r.get(k) or 0) for r in rows_)
    last28, prev28 = daily[-28:], daily[-56:-28]
    return {"ch": ch, "name": NAME(ch), **snap,
            "views28": s(last28, "views"), "views28_prev": s(prev28, "views"),
            "hours28": round(s(last28, "estimatedMinutesWatched") / 60, 1),
            "subs28": s(last28, "subscribersGained") - s(last28, "subscribersLost"),
            "spark": [int(r.get("views") or 0) for r in daily[-28:]]}


def route(event):
    h = event.get("headers") or {}
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    path = event.get("rawPath", "/")
    params = event.get("queryStringParameters") or {}
    body = event.get("body") or ""
    if event.get("isBase64Encoded") and body:
        body = base64.b64decode(body).decode()
    data = json.loads(body) if body else {}

    if path.startswith("/api/svc/"):
        if h.get("x-svc-token") != secret("svc_token"):
            return ok({"error": "forbidden"}, 403)
        if path == "/api/svc/control":
            return ok(get("CTRL", "MAIN", {}) or {})
        if path == "/api/svc/rotation" and method == "POST":
            put("ROT", "DAY#" + data["date"], data); return ok({"ok": True})
        if path == "/api/svc/sync" and method == "POST":     # order, start date, seeds from the repo's config
            c = get("CTRL", "MAIN", {}) or {}
            c.update({k: data[k] for k in ("order", "start_date", "seeds") if k in data}); c.setdefault("enabled", True)
            put("CTRL", "MAIN", c); return ok({"ok": True})
        return ok({"error": "not found"}, 404)

    who = user(event)
    if not who:
        return ok({"error": "sign in"}, 401)
    if path == "/api/me":
        return ok({"email": who, "last_collect": (get("SYS", "LASTCOLLECT", {}) or {}).get("at")})
    if path == "/api/overview":
        return ok({"channels": [summary(c) for c in CH_IDS()], "last_collect": (get("SYS", "LASTCOLLECT", {}) or {}).get("at")})
    if path == "/api/channel":
        ch = params.get("ch")
        if ch not in CH_IDS():
            return ok({"error": "unknown channel"}, 404)
        return ok({**summary(ch), "daily": get(f"CH#{ch}", "DAILY", []), "search": get(f"CH#{ch}", "SEARCH", []),
                   "traffic": get(f"CH#{ch}", "TRAFFIC", []), "topvideos": get(f"CH#{ch}", "TOPVIDEOS", []),
                   "uploads": get(f"CH#{ch}", "UPLOADS", [])})
    if path == "/api/rotation":
        ctrl = get("CTRL", "MAIN", {}) or {}
        days = sorted([d for _, d, _ in query("ROT", "DAY#")], key=lambda d: d.get("date", ""), reverse=True)[:21]
        return ok({"enabled": ctrl.get("enabled", True), "pins": ctrl.get("pins", {}), "bans": ctrl.get("bans", {}),
                   "schedule": schedule(ctrl), "days": days, "names": {c["id"]: c["name"] for c in channels()}})
    if path == "/api/rotation/control" and method == "POST":
        c = get("CTRL", "MAIN", {}) or {}; c["enabled"] = bool(data.get("enabled")); put("CTRL", "MAIN", c)
        return ok({"enabled": c["enabled"]})
    if path == "/api/topics" and method == "POST":
        ch, kw, act = data.get("ch"), (data.get("keyword") or "").strip(), data.get("action")
        if ch not in CH_IDS() or not kw or act not in ("pin", "ban", "clear"):
            return ok({"error": "bad request"}, 400)
        c = get("CTRL", "MAIN", {}) or {}
        for kind in ("pins", "bans"):
            lst = [k for k in c.setdefault(kind, {}).get(ch, []) if k.lower() != kw.lower()]
            if (act == "pin" and kind == "pins") or (act == "ban" and kind == "bans"):
                lst.append(kw)
            c[kind][ch] = lst
        put("CTRL", "MAIN", c)
        return ok({"pins": c["pins"].get(ch, []), "bans": c["bans"].get(ch, [])})
    if path == "/api/keywords":
        try:
            return ok(keywords(params))
        except Exception as e:
            return ok({"error": str(e)[:300]}, 502)
    if path == "/api/gsc":
        return ok({"sites": [d for _, d, _ in query("GSC")]})
    if path == "/api/collect" and method == "POST":
        boto3.client("lambda").invoke(FunctionName=os.environ["AWS_LAMBDA_FUNCTION_NAME"], InvocationType="Event",
                                      Payload=json.dumps({"collect": data.get("ch", "all")}).encode())
        return ok({"started": True})
    return ok({"error": "not found"}, 404)


def handler(event, context):
    if "collect" in event:
        return collect(event["collect"])
    try:
        return route(event)
    except Exception as e:
        print("ERROR", repr(e))
        return ok({"error": "server error"}, 500)
