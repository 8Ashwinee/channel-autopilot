# Troubleshooting: the problems people actually hit

| Symptom | Cause | Fix |
|---|---|---|
| `invalid_grant` a week after signing in | the OAuth app is still in **Testing** (Google cancels sign-ins after 7 days) | GOOGLE-SETUP §2: publish the app (In production), then `autopilot youtube-auth` again |
| "Access blocked: app has not completed the Google verification process" | app in Testing and the account is not a test user | publish the app (§2), or add the account as a test user |
| "Google hasn't verified this app" | an unverified app in production | normal for your own app: **Advanced → Go to … → Continue** |
| Sign-in for Google Ads ends on a "passkey" / "confirm it's really you" page | Google demands re-authentication for the Ads scope | use a **service account** for research (GOOGLE-SETUP §5–6) instead of a browser sign-in |
| Keyword Planner: `CLOUD_PROJECT_NOT_APPROVED_FOR_PRODUCTION` or permission denied | the Cloud project has Test or Explorer access | GOOGLE-SETUP §7: verify branding, then apply for **Basic** |
| `CUSTOMER_NOT_ENABLED` | the customer id is a client account still in draft (a skipped setup wizard) | use the **manager** account's id; it runs Keyword Planner itself |
| Research returns almost only brand names and logins | thresholds too high (1M+ searches) | 10,000–500,000 searches, `min_words: 3`, `--questions` |
| `uploadLimitExceeded` after a few uploads | a young channel's own daily limit, or the project's 10,000-unit quota | wait for the reset (midnight Pacific); phone-verify the channel; fewer uploads a day |
| Uploads stay private | API project not audited by YouTube, or `publish_at` in the future | apply for YouTube's API audit; scheduled items go public at their time |
| Custom thumbnail not set | the channel is not phone-verified, or the video is a Short | verify at youtube.com/verify; Shorts take no API thumbnail |
| Video over 15 minutes refused | channel not phone-verified | verify the channel |
| Dashboard: 403 from CloudFront on POST | the request lacks `x-amz-content-sha256` (CloudFront OAC in front of Lambda signs the body) | the dashboard's own pages send it; your own scripts must too |
| Dashboard shows no channels | `/chstudio/channels` not set | `dashboard/add_channel.py` for each channel |
| Dashboard: a channel's analytics are empty | its token lacks the analytics scope | `autopilot youtube-auth` again (0.2+ asks for it), then `add_channel.py` |
| The rotation made nothing for a video | the writer command wrote no video.yml | read `videos/<date>/<slug>.writer.log` in the channel folder |
