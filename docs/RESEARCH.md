# Keyword research: what people search for, and what it pays

`autopilot research` asks Google Ads Keyword Planner for every search related to your channel's topics, cleans the list
and ranks it, so each video answers a real question that advertisers pay to reach. Setup: [GOOGLE-SETUP.md](GOOGLE-SETUP.md)
steps 1, 5, 6 and 7. Install the extra: `pip install -e '.[research]'`.

## Configure

In the channel's `config.yml`:

```yaml
research:
  service_account_key: secrets/google-sa.json
  customer_id: "1234567890"          # your Google Ads (manager) account
  api_version: v26                   # Google Ads API version; raise it when Google retires the old one
  language: 1000                     # 1000 = English (Google's language constants)
  geo: 2840                          # 2840 = United States (Google's geo target constants)
  seeds:                             # 10 to 40 topics that describe your channel; Planner expands them
    - credit card debt
    - balance transfer
    - debt consolidation
  filters:
    min_searches: 10000              # monthly searches
    competition: LOW,MEDIUM          # advertiser competition
    min_bid: 3                       # top-of-page bid in the account's currency
    min_words: 3                     # specific questions, not head terms
  used_file: research/used.txt       # one topic per line; the rotation appends what it made
```

## Run

```bash
autopilot research                                  # the config's seeds and filters
autopilot research --seed "roth ira, 401k match"    # your own topics this once
autopilot research --min-searches 5000 --competition LOW --questions --limit 50 --csv research/today.csv
```

Output: how many ideas Planner returned, how many remained after merging misspellings, how many passed the filters, then
the list, best first.

## What it does with Planner's answer

1. **Merges misspellings.** Planner reports "chatgtp", "chadgbt", "chat_gpt" with exactly the same figures as "chatgpt".
   One row per cluster is kept: the clean spelling Planner ranked most relevant.
2. **Removes navigational searches**: people looking for a website or live data, not an answer ("gmail login", "near me",
   scores, schedules, weather, "tesla stock"). `--keep-navigational` keeps them.
3. **Skips topics already used** (`used_file`).
4. **Ranks by monthly searches × top-of-page bid**: a large audience that advertisers pay to reach.

## Reading the numbers honestly

- **Competition** is how many *advertisers* bid on the search in Google Ads. It says nothing about how many YouTube videos
  compete.
- **Bid** is what advertisers pay per Google Search click. It signals that a topic pays well. It is **not** your YouTube
  revenue per thousand views; real RPM shows in YouTube Analytics once a channel is monetised.
- **Avoid "1 million searches a month and low competition".** Measured on ~97,000 ideas: 308 matched, and almost all
  were someone typing a site's name ("youtube", "gmail", "weather", a sports team, a share price). No video answers them.
  10,000 to 500,000 searches, phrased as a question, is where videos win.
- Volumes are Google Search, not YouTube search. They are a good guide to what people want to know, not a forecast.
