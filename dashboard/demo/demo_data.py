"""Made-up data for the dashboard's demo screenshots (docs/media/dashboard-*.png). Fictional channels, invented numbers.

  python3 dashboard/demo/demo_data.py > /tmp/demo.json
"""
import json, math, datetime as dt

CH = [("daily-tech-tips", "Daily Tech Tips", "@dailytechtips", 18400, 2.1),
      ("money-basics", "Money Basics", "@moneybasics", 9200, 1.4),
      ("calm-corner", "Calm Corner", "@calmcorner", 3100, 0.8)]
today = dt.date(2026, 1, 20)


def daily(scale, seed):
    out = []
    for i in range(90):
        d = today - dt.timedelta(days=89 - i)
        w = 1 + 0.25 * math.sin(i / 3.5 + seed) + 0.004 * i * scale
        v = int(420 * scale * w + 60 * math.sin(i * 1.7 + seed))
        out.append({"day": d.isoformat(), "views": v, "estimatedMinutesWatched": int(v * 3.2),
                    "averageViewDuration": int(190 + 30 * math.sin(i / 5 + seed)),
                    "subscribersGained": max(0, int(v / 70 + 3 * math.sin(i))), "subscribersLost": max(0, int(v / 260))})
    return out


def summary(cid, name, handle, subs, scale, seed):
    d = daily(scale, seed)
    s = lambda rows, k: sum(r[k] for r in rows)
    return {"ch": cid, "name": name, "handle": handle, "subscribers": subs, "views": subs * 41, "videos": int(subs / 90),
            "monetized": subs > 5000, "thumb": "", "views28": s(d[-28:], "views"), "views28_prev": s(d[-56:-28], "views"),
            "hours28": round(s(d[-28:], "estimatedMinutesWatched") / 60, 1),
            "subs28": s(d[-28:], "subscribersGained") - s(d[-28:], "subscribersLost"), "spark": [r["views"] for r in d[-28:]]}, d


out = {"me": {"email": "you@example.com", "last_collect": "2026-01-20T05:15:00Z"}}
chans = []
for n, (cid, name, handle, subs, scale) in enumerate(CH):
    sm, d = summary(cid, name, handle, subs, scale, n)
    chans.append(sm)
    vids = [{"id": f"demo{n}{i}", "title": t, "published": f"2026-01-{18 - i * 2:02d}T17:30:00Z", "privacy": "public",
             "views": 4200 // (i + 1), "thumb": ""} for i, t in enumerate(
        {"daily-tech-tips": ["Live TV Streaming Services Compared: Which One Fits You (2026)", "How to Fix Wi-Fi That Keeps Dropping",
                             "Cloud Storage Explained: Which Plan Is Worth It", "Password Managers for Beginners"],
         "money-basics": ["Balance Transfer Cards: When They Save You Money", "The Rule of 72 Explained", "Debt Snowball vs Avalanche",
                          "How a High-Yield Savings Account Works"],
         "calm-corner": ["Box Breathing in 5 Minutes", "A 10-Minute Body Scan for Sleep", "How to Stop Overthinking at Night",
                         "Grounding: the 5-4-3-2-1 Technique"]}[cid])]
    sched = [{"id": f"next{n}{i}", "title": f"(scheduled) {t}", "publishAt": f"2026-01-{22 + i * 2}T17:30:00Z", "privacy": "private",
              "views": 0, "thumb": ""} for i, t in enumerate(["The next long video", "The one after"])]
    out[f"channel?ch={cid}"] = {**sm, "daily": d,
        "search": [{"insightTrafficSourceDetail": k, "views": v} for k, v in
                   {"daily-tech-tips": [("live tv streaming services", 812), ("best cloud storage", 455), ("wifi keeps disconnecting", 390), ("password manager", 288), ("streaming services compared", 204)],
                    "money-basics": [("balance transfer credit card", 640), ("rule of 72", 512), ("debt snowball", 301), ("high yield savings account", 280)],
                    "calm-corner": [("box breathing", 420), ("body scan meditation", 260), ("how to stop overthinking", 198)]}[cid]],
        "traffic": [{"insightTrafficSourceType": k, "views": int(v * scale)} for k, v in
                    [("YT_SEARCH", 5200), ("RELATED_VIDEO", 3100), ("SUBSCRIBER", 1500), ("SHORTS", 1200), ("EXT_URL", 600), ("PLAYLIST", 300)]],
        "topvideos": [{"video": v["id"], "views": v["views"], "estimatedMinutesWatched": v["views"] * 3, "averageViewDuration": 214,
                       "averageViewPercentage": 41 - i * 3, "subscribersGained": 30 - i * 5} for i, v in enumerate(vids)],
        "uploads": vids + sched}
out["overview"] = {"channels": chans, "last_collect": "2026-01-20T05:15:00Z"}
names = {c[0]: c[1] for c in CH}
out["rotation"] = {"enabled": True, "pins": {"money-basics": ["credit card consolidation loan"]}, "bans": {"daily-tech-tips": ["free movies online"]},
                   "names": names, "schedule": [{"date": (today + dt.timedelta(days=i)).isoformat(), "channel": CH[(i + 1) % 3][0]} for i in range(-1, 10)],
                   "days": [{"date": "2026-01-20", "channel": "daily-tech-tips", "status": "uploaded", "updated": "2026-01-20T08:20:00Z",
                             "topics": [{"keyword": "live tv streaming services", "searches": 2240000, "bid_high": 5.0},
                                        {"keyword": "cloud based data storage", "searches": 550000, "bid_high": 13.15},
                                        {"keyword": "best wifi extender for home", "searches": 40500, "bid_high": 2.1}],
                             "videos": [{"kind": "short", "keyword": "best wifi extender for home", "title": "Wi-Fi Dead Zones? One Fix That Works #Shorts", "queued": "q", "publish_at": "2026-01-20T17:30:00Z"},
                                        {"kind": "video", "keyword": "live tv streaming services", "title": "Live TV Streaming Services Compared: Which One Fits You (2026)", "queued": "q", "publish_at": "2026-01-22T17:30:00Z"},
                                        {"kind": "video", "keyword": "cloud based data storage", "title": "Cloud Storage Explained: Which Plan Is Worth It", "queued": "q", "publish_at": "2026-01-24T17:30:00Z"}]},
                            {"date": "2026-01-19", "channel": "calm-corner", "status": "uploaded", "updated": "2026-01-19T08:40:00Z",
                             "topics": [{"keyword": "box breathing technique", "searches": 33100, "bid_high": 1.2}],
                             "videos": [{"kind": "short", "keyword": "box breathing technique", "title": "Box Breathing in 30 Seconds #Shorts", "queued": "q", "publish_at": "2026-01-19T17:30:00Z"},
                                        {"kind": "video", "keyword": "body scan meditation for sleep", "failed": True, "reason": "the writer wrote no video.yml"}]}]}
gd = [{"keys": [(today - dt.timedelta(days=30 - i)).isoformat()], "clicks": int(40 + 15 * math.sin(i / 3)), "impressions": int(2100 + 500 * math.sin(i / 4)),
       "ctr": 0.02, "position": 9.5} for i in range(28)]
out["gsc"] = {"sites": [
    {"site": "sc-domain:dailytechtips.example", "start": "2025-12-21", "end": "2026-01-18", "daily": gd,
     "queries": [{"keys": [k], "clicks": c, "impressions": i, "ctr": c / i, "position": p} for k, c, i, p in
                 [("streaming services compared", 120, 3400, 6.2), ("fix wifi dropping", 88, 2900, 7.9), ("best cloud storage 2026", 61, 4100, 11.3)]],
     "pages": [{"keys": [f"https://dailytechtips.example{u}"], "clicks": c, "impressions": i} for u, c, i in
               [("/", 210, 5200), ("/streaming/", 140, 4100), ("/wifi-fixes/", 95, 3000)]],
     "countries": [{"keys": [k], "clicks": c, "impressions": i, "position": p} for k, c, i, p in [("usa", 520, 15000, 8.1), ("gbr", 90, 3100, 9.4)]]},
    {"site": "sc-domain:moneybasics.example", "start": "2025-12-21", "end": "2026-01-18",
     "daily": [{**r, "clicks": r["clicks"] // 2, "impressions": r["impressions"] // 2} for r in gd], "queries": [], "pages": [], "countries": []}]}
out["keywords"] = {"ideas": 1517, "merged": 1049, "passed": 14, "rows": [
    {"keyword": k, "searches": s, "competition": c, "bid_low": lo, "bid_high": hi, "score": round(s * hi), "state": st}
    for k, s, c, lo, hi, st in [("balance transfer credit card", 74000, "MEDIUM", 15.54, 47.35, ""), ("best balance transfer cards", 49500, "MEDIUM", 16.13, 43.17, ""),
                                ("zero percent interest credit cards", 40500, "MEDIUM", 17.47, 49.95, ""), ("credit card consolidation loan", 12100, "MEDIUM", 25.21, 76.07, "pinned"),
                                ("how to pay off credit card debt", 14800, "LOW", 6.1, 21.4, ""), ("debt consolidation calculator", 18100, "LOW", 3.2, 12.9, "")]]}
print(json.dumps(out))
