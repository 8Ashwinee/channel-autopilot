# channel-autopilot

<p align="center"><img src="docs/media/banner.png" alt="channel-autopilot: keyword research, AI writer, video maker, scheduler and dashboard, publishing to YouTube, Instagram and Facebook" width="100%"></p>

<p align="center">
  <img alt="YouTube and Shorts" src="https://img.shields.io/badge/YouTube%20%2B%20Shorts-FF0000?style=for-the-badge&logo=youtube&logoColor=white">
  <img alt="Instagram Reels and stories" src="https://img.shields.io/badge/Instagram%20Reels-E4405F?style=for-the-badge&logo=instagram&logoColor=white">
  <img alt="Facebook Reels and posts" src="https://img.shields.io/badge/Facebook%20Reels-1877F2?style=for-the-badge&logo=facebook&logoColor=white">
</p>
<p align="center">
  <img alt="Google Ads Keyword Planner" src="https://img.shields.io/badge/research-Keyword%20Planner-FBBC04?logo=googleads&logoColor=white">
  <img alt="Search Console" src="https://img.shields.io/badge/analytics-Search%20Console-458CF5?logo=googlesearchconsole&logoColor=white">
  <img alt="Dashboard on AWS" src="https://img.shields.io/badge/dashboard-your%20AWS-FF9900">
  <img alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white">
  <img alt="Free text-to-speech" src="https://img.shields.io/badge/voice-Kokoro%20TTS-8A2BE2">
  <img alt="MIT licence" src="https://img.shields.io/badge/licence-MIT-3CD278">
  <img alt="Version 0.2.0" src="https://img.shields.io/badge/version-0.2.0-555">
</p>

Run YouTube channels on autopilot with **your own keys**: find what people search for, write and make narrated videos,
publish them on a schedule to YouTube, Instagram and Facebook, rotate across several channels, and watch it all on a
private dashboard.

```
autopilot research ──► writer (your AI tool) ──► autopilot make ──► queue/ ──► autopilot run ──► YouTube · Instagram · Facebook
 Keyword Planner:        a video.yml per          voice, video,       go-live      daily caps,      + a daily report
 what people search      topic, sourced facts     captions, thumb     times        retries          + the dashboard
                         └─────────────── autopilot rotation: one channel a day, every day ───────────────┘
```

**No keys are included.** Every user brings their own Google Cloud project (YouTube API, Keyword Planner, Search
Console), their own Meta app if they post to Instagram/Facebook, and their own AWS account for the dashboard.
Start with [docs/GOOGLE-SETUP.md](docs/GOOGLE-SETUP.md).

## See it

**Videos it makes** (from the two example files in [`examples/videos/`](examples/videos/), free voice, rendered on a laptop):

| Short (9:16) | Long video (16:9) |
|:---:|:---:|
| <a href="docs/media/sample-short.mp4"><img src="docs/media/sample-short.gif" width="230" alt="A 28-second Short made by autopilot make"></a> | <a href="docs/media/sample-video.mp4"><img src="docs/media/sample-video.gif" width="460" alt="A 16:9 explainer made by autopilot make"></a> |
| [▶ Watch with sound](docs/media/sample-short.mp4) · [the script](examples/videos/three-habits-short.yml) | [▶ Watch with sound](docs/media/sample-video.mp4) · [the script](examples/videos/rule-of-72-video.yml) |

**The dashboard** (deployed into your own AWS account; demo channels and numbers):

| Every channel at a glance | One channel in depth |
|:---:|:---:|
| [![Overview](docs/media/dashboard-overview.png)](docs/media/dashboard-overview.png) | [![Channel page](docs/media/dashboard-channel.png)](docs/media/dashboard-channel.png) |
| **The daily rotation, with a pause switch** | **Keyword research: "Use next" / "Never"** |
| [![Rotation](docs/media/dashboard-rotation.png)](docs/media/dashboard-rotation.png) | [![Keyword research](docs/media/dashboard-keywords.png)](docs/media/dashboard-keywords.png) |

More: sample research output, a rotation day, a queue item, in [docs/SAMPLES.md](docs/SAMPLES.md).

| Guide | For |
|---|---|
| [docs/GOOGLE-SETUP.md](docs/GOOGLE-SETUP.md) | your Google keys, step by step: Cloud project, sign-in screen, YouTube sign-in per channel, service account, Google Ads Basic access, Search Console, quotas |
| [docs/SETUP.md](docs/SETUP.md) | Instagram/Facebook, media hosting, the daily report, running it daily |
| [docs/RESEARCH.md](docs/RESEARCH.md) | keyword research and how to read the numbers |
| [docs/ROTATION.md](docs/ROTATION.md) | several channels, fully automatic, one channel a day |
| [docs/DASHBOARD.md](docs/DASHBOARD.md) | the private dashboard in your AWS account |
| [docs/RESPONSIBLE-USE.md](docs/RESPONSIBLE-USE.md) | staying on the right side of YouTube's rules |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | the errors people actually hit, and the fixes |

The parts work alone or together:

| Part | What it does | Needs |
|---|---|---|
| **Publisher** | Posts a queue of videos, images and links to YouTube (videos and Shorts), Instagram (Reels, stories, images) and Facebook (Reels, stories, images, posts). Respects daily limits, retries failures, records everything in a local ledger, emails a daily report. | Python 3.10+, your own platform credentials |
| **Maker** | Turns a short `video.yml` (headlines, bullets, the lines to speak) into a narrated MP4 with captions and a thumbnail, using free open-source text-to-speech. | Python **3.10–3.12**, ffmpeg, espeak-ng, Chromium (via Playwright) |
| **Research** | Google Ads Keyword Planner over its REST API: every related search with monthly volume, competition and advertiser bid; misspellings merged, navigational searches removed, ranked by what pays. | a Google Cloud service account, a Google Ads account, Google Ads API Basic access |
| **Rotation** | Several channels, one channel a day: research → your writer command writes each video.yml → make → queue with go-live times → publish. | the above, plus a writer command (e.g. Claude Code headless) |
| **Dashboard** | A private web page in your AWS account: analytics per channel, YouTube search terms, the rotation (with a pause switch and topic choices), keyword research, Search Console. | an AWS account; about $0 a month |

Not included: accounts, platform approval, or any promise of views. You bring your own YouTube, Instagram and Facebook credentials; [docs/SETUP.md](docs/SETUP.md) walks through getting them.

## Quick start

```bash
git clone https://github.com/<you>/channel-autopilot && cd channel-autopilot
python3.12 -m venv .venv && . .venv/bin/activate
pip install -e '.[youtube,maker,research]'
playwright install chromium
brew install ffmpeg espeak-ng            # or: apt install ffmpeg espeak-ng

autopilot init                           # writes config.yml, queue/ and secrets/
autopilot make --setup                   # downloads the voice model (~330 MB, once)
autopilot make examples/videos/three-habits-short.yml --queue   # ~45 s: voice, video, thumbnail, queued
autopilot plan                           # what would post right now
autopilot run --dry-run                  # same, as a rehearsal: posts nothing
```

When your credentials are in `config.yml` ([docs/SETUP.md](docs/SETUP.md)):

```bash
autopilot doctor                         # which credentials are still missing
autopilot youtube-auth                   # one browser sign-in for YouTube
autopilot run --report                   # post what is due today, then email the report
autopilot research                       # topics worth a video (config: research:, docs/RESEARCH.md)
```

Several channels on autopilot: [docs/ROTATION.md](docs/ROTATION.md). Scheduled release of a queued video: add
`publish_at: 2026-01-07T17:30:00Z` to its item.yml (uploaded private, YouTube makes it public then); `comment:` posts the
first comment.

## The video maker

A `video.yml` describes scenes. Each scene has what is **shown** (a headline, numbered bullets, an image) and what is **said** (one or more lines). The timeline is built from the speech, so pictures and voice cannot drift apart.

```yaml
slug: three-focus-habits
kind: short                 # short = 1080x1920, video = 1920x1080
title: Three tiny habits that make focus easier
theme: {preset: calm}       # calm | bold | light, or your own colours
captions: true
scenes:
  - id: steps
    headline: The three habits
    bullets: [Phone out of sight, One task at a time, A two minute walk]
    say: [One. Phone out of sight., Two. One task at a time., Three. A two minute walk.]
```

Bullet *n* appears as line *n* is spoken. Put `*asterisks*` around a word to give it the accent gradient. `autopilot make --check` runs the voice and a layout check (text off the frame, a scene with more than fits) without rendering; `--still 6` writes one frame at 6 s to check the look.

## The publisher

The queue is a folder. Each item is a folder with an `item.yml` and its files:

```yaml
kind: short                 # short | video | image | post
title: Three tiny habits
description: ...            # YouTube description; the default caption
caption: ...                # Instagram and Facebook caption (optional)
tags: [focus, habits]
files: {video: video.mp4, thumbnail: thumb.jpg}
```

A `short` goes to YouTube Shorts, an Instagram Reel and story, and a Facebook Reel and story. A `video` goes to YouTube. An `image` goes to Instagram and Facebook. A `post` is a Facebook link post. Override with `actions:` per item or `default_actions:` in the config.

How a day works:

- Every action has a daily limit in `limits:` (defaults: 2 Shorts, 2 videos, 1 of everything else). `autopilot run` posts the next queued items up to each limit, in `priority` order.
- A platform's day can start at its own hour (`youtube.reset_hour: 8`: YouTube's upload cap resets at 08:00 UTC).
- If a platform says stop for today (upload cap, publishing quota) the run stops that action, leaves the item for tomorrow, and does not count it as a failure.
- Any other error is recorded and the item is retried on a later run, up to `max_attempts` (3), without stopping the rest of the day.
- A post that succeeded is never posted again. The ledger is written right after each successful post; if the process were killed in the instant between the platform accepting a post and the ledger write, that one post could be repeated.
- `autopilot report` (or `run --report`) builds the daily report: every live URL posted that day, failures, and what is still queued. Send it by SMTP or Amazon SES, or just print it.

Run it every day with cron or launchd: see [docs/SETUP.md](docs/SETUP.md). A laptop that sleeps runs the job when it wakes, not at an exact time.

## Platform rules, in plain words

- **YouTube:** videos uploaded through the API from a Google Cloud project that has not passed YouTube's API audit can be locked to private. Check Google's current rules for your project before relying on public uploads. Refresh tokens for an OAuth app left in "Testing" expire after about a week, so publish the consent screen (or re-run `youtube-auth`).
- **Instagram and Facebook:** posting to your own Page and Instagram business account works with a developer app in which you are an admin. Posting for other people's accounts needs Meta's App Review and business verification. Instagram allows 100 API-published posts per 24 hours per account.
- You are responsible for following each platform's terms and for what you publish. This project is not affiliated with Google, Meta or any platform.

## What it does not do

It does not create accounts or get platform approvals for you, ship any keys, edit existing videos, or post to TikTok, X or
LinkedIn (adding a platform means one module in `src/autopilot/platforms/`). Script writing is done by the writer command
**you** configure (any AI tool or script); the project supplies the prompt template and the rules, not an AI account.

## Licences of what it uses

This project is MIT. It *calls* these, and does not bundle them: [Kokoro](https://github.com/hexgrad/Kokoro-82M) text-to-speech (open-weight, Apache-2.0) through `kokoro-onnx`, Playwright and Chromium, and your own `ffmpeg` (check the licence of the build you installed: many are GPL). The voice model is downloaded on first use, not shipped. Music, fonts and images are yours: nothing is included.

## Development

```bash
pip install -e '.[dev,youtube,maker,research]' && pytest      # the tests mock the network; nothing is posted
```
