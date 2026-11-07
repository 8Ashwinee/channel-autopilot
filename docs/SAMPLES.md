# Samples: what each command gives you

Real output where it is public data (Keyword Planner figures), demo channel names everywhere else.

## `autopilot research`

```text
$ autopilot research --seed "credit card debt, balance transfer" --min-bid 3 --min-words 3 --limit 6
1,517 ideas, 1,049 after merging misspellings, 14 passed {'min_searches': 10000, 'competition': 'LOW,MEDIUM', 'min_bid': 3.0, 'min_words': 3}
    74,000  MEDIUM  $15.54-47.35    balance transfer credit card
    49,500  MEDIUM  $16.13-43.17    best balance transfer cards
    40,500  MEDIUM  $17.47-49.95    zero percent interest credit cards
    27,100  LOW     $5.85-39.7      wells fargo reflect card balance transfer
    12,100  MEDIUM  $25.21-76.07    credit card consolidation loan
    18,100  MEDIUM  $18.47-50.0     0 balance transfer credit cards
```

Monthly US Google searches, advertiser competition, the top-of-page bid range. Each line is a video someone is looking for,
on a topic advertisers pay to reach. ([RESEARCH.md](RESEARCH.md) explains the numbers.)

## `autopilot rotation status`

```text
$ autopilot rotation status
2026-01-18 calm-corner      3 queued
2026-01-19 daily-tech-tips  3 queued
2026-01-20 money-basics     3 queued     ← today
2026-01-21 calm-corner
2026-01-22 daily-tech-tips
2026-01-23 money-basics
```

## A rotation day (`rotation-days/2026-01-20.json`)

```json
{
 "date": "2026-01-20",
 "channel": "Money Basics",
 "topics": [
  {"keyword": "balance transfer credit card", "searches": 74000, "competition": "MEDIUM", "bid_low": 15.54, "bid_high": 47.35, "score": 3503900},
  {"keyword": "best balance transfer cards", "searches": 49500, "competition": "MEDIUM", "bid_low": 16.13, "bid_high": 43.17, "score": 2136915},
  {"keyword": "zero percent interest credit cards", "searches": 40500, "competition": "MEDIUM", "bid_low": 17.47, "bid_high": 49.95, "score": 2022975}
 ],
 "videos": [
  {"kind": "short", "keyword": "balance transfer credit card", "title": "Balance Transfer Card: Is the Fee Worth It? #Shorts",
   "queued": "queue/balance-transfer-credit-card-0120", "publish_at": "2026-01-20T17:30:00Z"},
  {"kind": "video", "keyword": "best balance transfer cards", "title": "Best Balance Transfer Cards: How to Pick One (2026)",
   "queued": "queue/best-balance-transfer-cards-0120", "publish_at": "2026-01-22T17:30:00Z"},
  {"kind": "video", "keyword": "zero percent interest credit cards", "title": "0% Interest Credit Cards Explained: What Happens When It Ends",
   "queued": "queue/zero-percent-interest-credit-cards-0120", "publish_at": "2026-01-24T17:30:00Z"}
 ]
}
```

## A queued video (`queue/<slug>/item.yml`)

```yaml
kind: video
title: "Best Balance Transfer Cards: How to Pick One (2026)"
description: |
  The best balance transfer card is the one whose 0% period outlasts your payoff plan, with a fee you can recover...
  Sources: https://www.consumerfinance.gov/... (every URL the video's numbers come from)
  For education only, not financial advice.
tags: [best balance transfer cards, balance transfer credit card, 0% apr, ...]
files: {video: video.mp4, thumbnail: thumb.jpg}
publish_at: "2026-01-22T17:30:00Z"     # uploaded private, public at this time
comment: "Have you used a balance transfer before? Did the fee pay off?"
```

## The daily report (email)

Every live URL posted that day, what failed and why, and what is still queued, by platform: see
[SETUP.md §4](SETUP.md).
