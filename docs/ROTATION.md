# The rotation: several channels, fully automatic, one channel a day

The rotation runs a network of channels on its own. Every day it takes the next channel in your list and:

```
keyword research ──► writer (an AI command you choose) ──► autopilot make ──► queue with go-live times ──► publish
 topics the channel      writes a video.yml per video,        voice, video,      Short today, long videos      the channel's
 never covered           facts from sources                   captions, thumbnail +2 and +4 days               daily limits apply
```

Default: **1 Short + 2 long videos a day for one channel**. With 6 channels each channel makes 3 videos every 6 days and,
because the releases are spread, publishes something about every 2 days. That pace fits YouTube's API quota (about 6
uploads a day for all your channels together, [GOOGLE-SETUP.md](GOOGLE-SETUP.md) §9) and stays far from mass production.

## 1. Folder layout

```
my-network/
  rotation.yml          # the order, the pace, the release times, the writer
  writer.md             # instructions for the writer, with {placeholders}
  rotation-days/        # one state file per day (written by the rotation)
tech-channel/           # an ordinary autopilot folder per channel
  config.yml            # its own YouTube sign-in, research block, brief, limits
  secrets/              # youtube-oauth-client.json, youtube-token.json, google-sa.json
  queue/  videos/  out/  state.db
money-channel/
  ...
```

## 2. Set up each channel

For each channel:

```bash
mkdir tech-channel && cd tech-channel
autopilot init                       # config.yml, queue/, secrets/
# put the OAuth client JSON in secrets/ (GOOGLE-SETUP.md §3), then:
autopilot youtube-auth               # sign in AS THIS CHANNEL
```

Then add to its `config.yml`:

```yaml
name: Tech Channel
brief: >                             # read by the writer for every video: who the channel is for, tone, what to avoid
  Practical tech tutorials for beginners: streaming, smartphones, AI tools. Friendly, step by step, no hype.
  Never show other companies' logos or app screens; describe them.
research: { ... }                    # docs/RESEARCH.md
youtube:
  client_secret: secrets/youtube-oauth-client.json
  token: secrets/youtube-token.json
  privacy: public
  category: "28"                     # Science & Technology (27 Education, 26 Howto & Style, 22 People & Blogs)
  reset_hour: 8                      # YouTube's quota day starts at midnight Pacific = 08:00 UTC (07:00 in summer)
limits:
  youtube.short: 2
  youtube.video: 2
default_actions:                     # YouTube only, unless you also want Instagram/Facebook
  short: [youtube.short]
  video: [youtube.video]
```

Run `autopilot research` in it once to check the topics look right.

## 3. The rotation file

Copy `examples/rotation/rotation.yml` and `examples/rotation/writer.md` into `my-network/` and edit:

```yaml
start_date: 2026-01-05               # day 0: the first channel in the list
channels: [../tech-channel, ../money-channel, ../health-channel]
per_day: {short: 1, video: 2}
release:
  time: "12:30"                      # go-live time...
  timezone: America/New_York         # ...in this time zone
  offsets_days: {short: [0], video: [2, 4]}
lengths: {short: "35 to 55 seconds of speech", video: "8 to 10 minutes of speech"}
writer:
  command: [claude, -p, "{prompt}", --dangerously-skip-permissions, --allowedTools, "Read Write Edit WebFetch WebSearch", --max-turns, "120"]
  prompt_file: writer.md
  timeout: 3600
```

**The writer** is any command that writes the video.yml at the `{spec}` path. The example uses Claude Code in headless
mode (you need your own Claude Code installation and account); you can swap in another AI tool or a script of your own.
The prompt template (`writer.md`) gets `{channel} {brief} {kind} {keyword} {searches} {bid} {spec} {date} {length}`.
Keep the rules in it: sourced facts only, honest titles, disclaimers for money/law/health, no background processes.

## 4. Try it, then schedule it

```bash
cd my-network
autopilot rotation status            # which channel on which day (--json for JSON output)
autopilot rotation plan              # today's channel and the 3 topics it would use; makes nothing
autopilot rotation run               # research, write, make, queue (about 30-90 minutes)
autopilot rotation run --publish     # same, then runs that channel's publisher (`autopilot run --report`)
```

Look at the first few videos yourself before you schedule it. Then run it daily, e.g. with cron at 09:00:

```cron
0 9 * * * cd /path/to/my-network && /path/to/.venv/bin/autopilot rotation run --publish >> rotation.log 2>&1
```

On macOS use launchd (see `examples/com.example.autopilot.plist`); a sleeping laptop runs the job when it wakes.
Run the publisher of **every** channel daily as well (`autopilot run` in each folder), so scheduled items that were not
uploaded on their day (quota reached) go out the next day.

## 5. What happens when something fails

- Every step is recorded in `rotation-days/<date>.json`. Running the same day again continues where it stopped.
- If the writer writes nothing, or the render fails, that video is marked `failed` with the reason; the others continue.
- A topic is recorded as used (`research/used.txt`) only after its video is queued.
- Uploads respect each channel's `limits` and YouTube's quota; anything over the limit waits for the next run.
- Uploads with a go-live time are uploaded **private** and YouTube makes them public at that time.

## 6. With the dashboard

If you deploy the dashboard ([DASHBOARD.md](DASHBOARD.md)), add:

```yaml
dashboard: {url: "https://your-dashboard.example.com", token_file: "~/secrets/studio-token"}
```

The rotation then reports each day to it, sends it the order and each channel's seeds, and obeys it: **Pause** stops the
next run before it makes anything; **Use next** topics are made first on that channel's next day; **Never** topics are
skipped. Channel ids on the dashboard are the channel **folder names**.

## 7. Read this before you automate a network

[RESPONSIBLE-USE.md](RESPONSIBLE-USE.md). YouTube removes and demonetises channels that publish repetitive,
mass-produced content. Automation is fine; low-effort sameness is not.
