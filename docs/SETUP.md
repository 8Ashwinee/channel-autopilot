# Setup

## 1. YouTube

Follow [GOOGLE-SETUP.md](GOOGLE-SETUP.md) §1–4: your own Cloud project, the published sign-in screen, the OAuth client JSON in `secrets/youtube-oauth-client.json`, then `autopilot youtube-auth` signed in as the channel. §9 explains the quota.

## 2. Instagram and Facebook (one Meta token)

You need an **Instagram business or creator account linked to a Facebook Page**, and a Meta developer app.

1. [developers.facebook.com](https://developers.facebook.com/) → create an app (type *Business*), add the Facebook Login for Business and Instagram products.
2. In Business Settings, create a **system user**, give it admin access to your Page, your Instagram account and the app, and generate a token with: `instagram_content_publish`, `instagram_basic`, `pages_manage_posts`, `pages_read_engagement`, `publish_video`, `pages_show_list`.
3. Find the ids: the Page id (Page → About → Page transparency) and the Instagram account id (`GET /{page-id}?fields=instagram_business_account`).
4. Put them in the environment (or directly in `config.yml`): `META_TOKEN`, `IG_ACCOUNT_ID`, `FB_PAGE_ID`. Never commit them.

Posting to your own accounts works while the app is in development mode with you as admin. Posting for other people's accounts needs App Review.

## 3. Media hosting (Instagram and Facebook fetch from a public URL)

Either an S3 bucket reachable at a public URL (the `aws` CLI must be configured):

```yaml
media:
  s3_bucket: my-bucket
  public_base: https://cdn.example.com/
  prefix: autopilot/
```

or any command of yours that uploads a file and prints its public https URL:

```yaml
media:
  command: "my-uploader {path} {name}"
```

## 4. The daily report

```yaml
email:
  method: ses           # none | smtp | ses
  to: you@example.com
  from: autopilot@your-verified-domain.com
  region: us-east-1     # ses only; the sender must be verified in SES
```

SMTP needs `host`, `port`, `user`, `password` under `email:`.

## 5. Run it daily

cron (every day at 12:30 local):

```
30 12 * * *  cd /path/to/project && .venv/bin/autopilot run --report >> autopilot.log 2>&1
```

macOS launchd: copy `examples/com.example.autopilot.plist`, edit the paths, `launchctl load` it. A Mac that is asleep runs the job when it wakes.

Start with `autopilot run --dry-run` for a day. Then run it for real once by hand and look at what it posted before you schedule it.

## 6. Make a video

```bash
autopilot make --setup                       # voice model, once
autopilot make my-video.yml --queue          # voice + video + thumbnail, then queued
```

The maker needs Python 3.10–3.12 (its speech library has no 3.13/3.14 build yet), `ffmpeg`, `espeak-ng` and Chromium (`playwright install chromium`). If `espeak-ng` is not found, set `PHONEMIZER_ESPEAK_LIBRARY` to its library file.
