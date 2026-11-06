# channel-autopilot

Make a narrated video from a text file, then publish it every day to YouTube, Instagram and Facebook, with a daily report that lists every live URL.

```
video.yml ──► autopilot make ──► queue/ ──► autopilot run (daily) ──► YouTube · Instagram · Facebook
 (script)      (voice + video)    (items)     (caps, retries,           + a daily report with every live URL
                                               never posts twice)
```

Two parts that work alone or together:

| Part | What it does | Needs |
|---|---|---|
| **Publisher** | Posts a queue of videos, images and links to YouTube (videos and Shorts), Instagram (Reels, stories, images) and Facebook (Reels, stories, images, posts). Respects daily limits, retries failures, records everything in a local ledger, emails a daily report. | Python 3.10+, your own platform credentials |
| **Maker** | Turns a short `video.yml` (headlines, bullets, the lines to speak) into a narrated MP4 with captions and a thumbnail, using free open-source text-to-speech. | Python **3.10–3.12**, ffmpeg, espeak-ng, Chromium (via Playwright) |

Not included: accounts, platform approval, or any promise of views. You bring your own YouTube, Instagram and Facebook credentials; [docs/SETUP.md](docs/SETUP.md) walks through getting them.

## Quick start

```bash
git clone https://github.com/<you>/channel-autopilot && cd channel-autopilot
python3.12 -m venv .venv && . .venv/bin/activate
pip install -e '.[youtube,maker]'
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
```

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

It does not write your scripts, pick topics, create accounts or get platform approvals, edit existing videos, or post to TikTok, X or LinkedIn (the action list is small on purpose; adding a platform means one module in `src/autopilot/platforms/`).

## Licences of what it uses

This project is MIT. It *calls* these, and does not bundle them: [Kokoro](https://github.com/hexgrad/Kokoro-82M) text-to-speech (open-weight, Apache-2.0) through `kokoro-onnx`, Playwright and Chromium, and your own `ffmpeg` (check the licence of the build you installed: many are GPL). The voice model is downloaded on first use, not shipped. Music, fonts and images are yours: nothing is included.

## Development

```bash
pip install -e '.[dev,youtube,maker]' && pytest      # the tests mock the network; nothing is posted
```
