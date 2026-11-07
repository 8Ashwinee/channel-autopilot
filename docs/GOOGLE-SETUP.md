# Google setup: YouTube, Keyword Planner and Search Console with your own keys

channel-autopilot ships with **no keys of its own**. Everything below happens in **your** Google accounts, and the keys stay
on **your** machine (and, if you deploy the dashboard, in **your** AWS account). Budget about an hour the first time.

You will end up with:

| Key | What it is for | Where it lives |
|---|---|---|
| OAuth client (Desktop app) JSON | lets the tool ask you to sign in to each YouTube channel | `secrets/youtube-oauth-client.json` in each channel folder |
| One YouTube token per channel | uploads, scheduling, captions, comments, analytics for that channel | `secrets/youtube-token.json` in that channel's folder |
| Service account key JSON | Keyword Planner and Search Console, no browser sign-in | `secrets/google-sa.json` (path set in `research.service_account_key`) |
| Google Ads customer id | the Google Ads account that runs Keyword Planner | `research.customer_id` in config.yml |

Never commit any of these. `autopilot init` creates a `secrets/` folder and a `.gitignore` for it.

---

## 1. A Google Cloud project

1. Open <https://console.cloud.google.com/>, signed in with the Google account you want to own the project.
2. Project picker → **New project** → give it a name (e.g. `my-channels`) → **Create**. Select it.
3. **APIs & Services → Library**, and enable each of these:
   - **YouTube Data API v3** (uploads, metadata, playlists, comments)
   - **YouTube Analytics API** (views, watch time, search terms; used by the dashboard)
   - **Google Ads API** (Keyword Planner)
   - **Google Search Console API** (only if you use the dashboard's Search Console pages)

All four are free. You do not need a billing account for them, but see the note on billing in step 6.

## 2. The sign-in screen (OAuth consent) — publish it

Google calls this **Google Auth Platform** in the console menu.

1. **Branding**: app name (anything, e.g. "My channels uploader"), user support email, developer contact email.
   Add an application home page, a privacy policy link and a terms link on a domain you own, and add that domain under
   **Authorized domains**. **Do not upload a logo**: a logo makes Google require a full verification review.
2. **Audience**: user type **External**. Then press **Publish app** so the status reads **In production**.
   - Why: while an app is in **Testing**, Google cancels every sign-in after **7 days** and only listed test users can sign
     in. In production, sign-ins do not expire (a token unused for 6 months still lapses).
   - You do **not** need Google's verification for your own use (up to 100 users). Each sign-in then shows
     *"Google hasn't verified this app"*: click **Advanced → Go to <app name> → Continue**. It is your own app.
3. **Data access** (scopes) can stay empty: the tool asks for the scopes it needs when you sign in.

## 3. The OAuth client (one JSON for all your channels)

1. **Google Auth Platform → Clients → Create client** → type **Desktop app** → name it → **Create**.
2. **Download JSON**. Copy it into each channel folder as `secrets/youtube-oauth-client.json`
   (or point `youtube.client_secret` at one shared copy).

## 4. Sign in to each channel

In each channel folder:

```bash
autopilot youtube-auth
```

A browser opens. Choose the Google account that **owns the channel**; if that account has several channels (brand
accounts), Google asks which one: pick the right channel. Confirm the "unverified app" screen (step 2) and **Allow**.
The token is saved to `secrets/youtube-token.json` (permissions 600).

Check it: `autopilot doctor`. If you sign in with the wrong channel, delete the token and run `youtube-auth` again.

**Before you upload a lot, on each channel:**
- Verify the channel with a phone number at <https://www.youtube.com/verify>. Without it YouTube refuses videos longer
  than 15 minutes and custom thumbnails.
- New channels have their own small daily upload limit (a handful a day) on top of the API quota below.

## 5. A service account (Keyword Planner and Search Console without browser sign-ins)

Keyword Planner over the API needs a Google identity with access to a Google Ads account. A **service account** is the
reliable way: it never needs a browser, never expires and is never asked for a passkey. (Signing in interactively for
the Google Ads scope often triggers Google's "confirm it's really you" passkey check, which a script cannot pass.)

1. **IAM & Admin → Service accounts → Create service account** → name it → **Done** (no roles needed).
2. Open it → **Keys → Add key → Create new key → JSON**. Save the file as `secrets/google-sa.json`. Treat it like a password.
3. Note its email address, `name@project-id.iam.gserviceaccount.com`. You add it as a user in steps 6 and 8.

## 6. Google Ads: an account that runs Keyword Planner

Keyword Planner is part of Google Ads. You need an account, **not** a campaign and **not** ad spend.

1. Go to <https://ads.google.com/home/tools/manager-accounts/> → **Create a manager account**.
   - Choose **Manage my own accounts**, your country, time zone and **currency carefully: they can never be changed**.
   - A manager account runs Keyword Planner itself; you do not need a client account under it. If Google pushes you into
     "create your first campaign", close it (the ✕ at the top left).
2. Its **customer id** is shown at the top right (`123-456-7890`). Put it in `research.customer_id` (dashes optional).
3. **Admin → Access and security → Users → +** → paste the **service account email** → access level **Standard** →
   **Send invitation**. Service accounts are added at once; there is no invitation to accept.

## 7. Google Ads API access for your Cloud project (Basic)

Google retired developer tokens on **9 September 2026**. API access now belongs to the **Cloud project** whose credentials
make the call (here: the project of your service account). The old **API Center** form in Google Ads is now only for the
App Conversion Tracking API: do not use it.

1. Cloud console → **Google Auth Platform → Branding** → (with the fields from step 2 filled in) **Verify branding**, then
   **Publish branding**. This takes a few minutes. It is a prerequisite for Basic access.
2. Open the **Google Ads API Overview** page: <https://console.cloud.google.com/google/ads-apis/overview> (your project
   selected). New projects show **Explorer** access.
3. Under **Upgrade access level → Basic**, click **Apply for access**. The review is automatic and usually takes minutes;
   you get an email and the page shows **Basic**.

Why Basic: **Explorer** access excludes all planning services, including Keyword Planner (`KeywordPlanIdeaService`).
If the application is refused, Google's known cause is a Cloud project on a free-trial or suspended billing account.

Test it:

```bash
autopilot research --seed "credit card debt" --limit 5
```

## 8. Search Console (only for the dashboard)

For each property at <https://search.google.com/search-console>: **Settings → Users and permissions → Add user** → the
service account email → **Restricted** (read is enough) or **Full**. The dashboard lists every property it can read.

## 9. Quotas you will meet

- **YouTube Data API: 10,000 units a day per Cloud project**, shared by **every channel and every person** using that
  project's OAuth client. An upload costs about 1,600 units, so about **6 uploads a day in total**. Captions (~400),
  thumbnails (50), comments (50) and playlist inserts (50) add up. The rotation's default (3 videos a day) leaves room.
- Need more? Request a quota extension with Google's *YouTube API Services* audit form. **Do not create extra Cloud
  projects to get around the quota**: it breaks the YouTube API Services terms and can get the projects banned.
- The quota resets at **midnight US Pacific time**; set `youtube.reset_hour` so the publisher's day starts then.
- Google Ads API (Basic): 15,000 operations a day. A research run uses one request per 20 seed topics.
- YouTube may lock uploads from an API project that has not passed its audit to private. If yours are locked, apply for
  the audit; the tool cannot change that.
