"""Keyword research with Google Ads Keyword Planner (REST, no Google Ads library needed).

config.yml:
  research:
    service_account_key: secrets/google-sa.json   # a Google Cloud service account added as a user of your Google Ads account
    customer_id: "1234567890"                      # the Google Ads account (a manager account works) that runs Keyword Planner
    api_version: v26                               # Google Ads API version
    language: 1000                                 # language constant (1000 = English)
    geo: 2840                                      # geo target constant (2840 = United States)
    seeds: [credit card debt, balance transfer]    # your channel's topics: Keyword Planner expands them
    filters: {min_searches: 10000, competition: "LOW,MEDIUM", min_bid: 1, min_words: 3}
    used_file: research/used.txt                   # topics already made (one per line), skipped next time

Access: the Google Cloud project that owns the service account needs Google Ads API access at Basic level or higher
(Keyword Planner is not available at the Test or Explorer level). Developer tokens are not needed (sunset in 2026).

Reading the numbers: "competition" is ADVERTISER competition on Google Search, not how many videos compete; the bid is
what advertisers pay per search click, a sign that a topic pays, not a YouTube RPM. A threshold of a million searches a
month finds almost only navigational searches (people looking for a website), which no video answers.
"""
from __future__ import annotations

import csv
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

from .errors import ConfigError

NAVIGATIONAL = re.compile(
    r"\b(login|log in|sign in|signin|sign up|www|\.com|com|near me|app download|customer service|phone number|hours|"
    r"address|stock price|ticker|futures|today|tonight|tomorrow|live score|scores?|standings|schedule|tickets|weather|"
    r"radar|forecast|official site|website|apk|download|free online|watch online)\b", re.I)
TICKER = re.compile(r"^\S+ stocks?$", re.I)          # "tesla stock": a price lookup
QUESTION = re.compile(r"^(how|what|why|can|should|is|are|does|do|when|which|who|where|will)\b", re.I)


def access_token(key_file: Path, scope: str = "https://www.googleapis.com/auth/adwords") -> str:
    """Service-account access token by the JWT-bearer grant (google-auth signs; urllib exchanges)."""
    try:
        from google.auth import crypt, jwt
    except ImportError:
        raise ConfigError("research needs: pip install 'channel-autopilot[research]'") from None
    info = json.loads(Path(key_file).read_text())
    now = int(time.time())
    signer = crypt.RSASigner.from_service_account_info(info)
    assertion = jwt.encode(signer, {"iss": info["client_email"], "scope": scope, "aud": "https://oauth2.googleapis.com/token",
                                    "iat": now, "exp": now + 3600}).decode()
    form = urllib.parse.urlencode({"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion}).encode()
    with urllib.request.urlopen(urllib.request.Request("https://oauth2.googleapis.com/token", data=form), timeout=30) as r:
        return json.loads(r.read())["access_token"]


def ideas(token: str, customer_id: str, seeds: list, version="v26", language=1000, geo=2840) -> list[dict]:
    """Every Keyword Planner idea around the seeds (20 seeds per request), in Planner's relevance order."""
    out: dict = {}
    for i in range(0, len(seeds), 20):
        body = {"language": f"languageConstants/{language}", "geoTargetConstants": [f"geoTargetConstants/{geo}"],
                "keywordPlanNetwork": "GOOGLE_SEARCH", "includeAdultKeywords": False,
                "keywordSeed": {"keywords": seeds[i:i + 20]}, "pageSize": 10000}
        req = urllib.request.Request(f"https://googleads.googleapis.com/{version}/customers/{customer_id}:generateKeywordIdeas",
                                     data=json.dumps(body).encode(),
                                     headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            res = json.loads(r.read()).get("results", [])
        for x in res:
            m = x.get("keywordIdeaMetrics", {})
            out.setdefault(x["text"], {"keyword": x["text"], "rank": len(out),
                                       "searches": int(m.get("avgMonthlySearches", 0) or 0),
                                       "competition": m.get("competition", "UNSPECIFIED"),
                                       "competition_index": int(m.get("competitionIndex", 0) or 0),
                                       "bid_low": round(int(m.get("lowTopOfPageBidMicros", 0) or 0) / 1e6, 2),
                                       "bid_high": round(int(m.get("highTopOfPageBidMicros", 0) or 0) / 1e6, 2)})
    return list(out.values())


def merge_misspellings(rows: list[dict]) -> list[dict]:
    """Planner gives a misspelling exactly its parent's figures: keep one per cluster, the clean, most relevant form."""
    groups: dict = {}
    for r in rows:
        groups.setdefault((r["searches"], r["competition_index"], r["bid_low"], r["bid_high"]), []).append(r)
    kept = []
    for g in groups.values():
        g.sort(key=lambda r: (bool(re.search(r"\d|[^\x00-\x7f]|_", r["keyword"])), r["rank"]))
        kept.append(g[0])
    return kept


def select(rows: list[dict], min_searches=10000, max_searches=10**12, competition="LOW,MEDIUM", min_bid=0.0,
           min_words=2, questions=False, keep_navigational=False, skip=()) -> list[dict]:
    """Filter and rank by monthly searches x top-of-page bid (a large audience that advertisers pay to reach)."""
    comp = {c.strip().upper() for c in str(competition).split(",")}
    skip = {s.lower() for s in skip}
    out = []
    for r in rows:
        k = r["keyword"]
        if not (min_searches <= r["searches"] <= max_searches) or r["competition"] not in comp or r["bid_high"] < min_bid:
            continue
        if len(k.split()) < min_words or k.lower() in skip:
            continue
        if not keep_navigational and (NAVIGATIONAL.search(k) or TICKER.search(k)):
            continue
        if questions and not QUESTION.search(k):
            continue
        out.append({**{x: r[x] for x in ("keyword", "searches", "competition", "bid_low", "bid_high")},
                    "score": round(r["searches"] * r["bid_high"])})
    return sorted(out, key=lambda r: -r["score"])


def used(cfg) -> set:
    p = cfg.path("research.used_file", "research/used.txt")
    return {l.strip().lower() for l in p.read_text().splitlines() if l.strip()} if p.exists() else set()


def mark_used(cfg, keywords):
    p = cfg.path("research.used_file", "research/used.txt")
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a") as fh:
        for k in keywords:
            fh.write(k + "\n")


def run(cfg, seeds=None, **overrides) -> dict:
    r = cfg.get("research") or {}
    if not r:
        raise ConfigError("no research: block in config.yml (see autopilot/research.py)")
    seeds = seeds or r.get("seeds") or []
    if not seeds:
        raise ConfigError("research.seeds is empty: give your channel's topics, or pass --seed")
    tok = access_token(cfg.path("research.service_account_key", "secrets/google-sa.json"))
    raw = ideas(tok, str(r["customer_id"]).replace("-", ""), seeds, r.get("api_version", "v26"), r.get("language", 1000), r.get("geo", 2840))
    merged = merge_misspellings(raw)
    f = {**(r.get("filters") or {}), **{k: v for k, v in overrides.items() if v is not None}}
    rows = select(merged, skip=used(cfg), **f)
    return {"ideas": len(raw), "merged": len(merged), "rows": rows, "filters": f, "seeds": seeds}


def write_csv(rows, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["keyword", "searches", "competition", "bid_low", "bid_high", "score"])
        w.writeheader(); w.writerows(rows)
