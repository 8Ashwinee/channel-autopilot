"""YouTube Data API v3 (needs the optional `youtube` extra: pip install 'channel-autopilot[youtube]').

config:
  youtube:
    client_secret: secrets/youtube-oauth-client.json   # OAuth "Desktop app" client from Google Cloud Console
    token: secrets/youtube-token.json                   # written by `autopilot youtube-auth`
    privacy: public                                     # public | unlisted | private
    category: "22"
One upload costs 1,600 of the default 10,000 daily quota units, so about six uploads a day.
"""
from __future__ import annotations

from ..errors import AutopilotError, ConfigError, QuotaReached
from . import Result

# youtube: upload and manage; force-ssl: comments; yt-analytics.readonly: the dashboard's analytics (read only)
SCOPES = ["https://www.googleapis.com/auth/youtube", "https://www.googleapis.com/auth/youtube.force-ssl",
          "https://www.googleapis.com/auth/yt-analytics.readonly"]


def _libs():
    try:
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        raise ConfigError("YouTube needs: pip install 'channel-autopilot[youtube]'") from None
    return build, HttpError, MediaFileUpload


def auth(cfg):
    """One-time browser sign-in as the channel owner; saves the token."""
    from google_auth_oauthlib.flow import InstalledAppFlow
    secret, token = cfg.path("youtube.client_secret", "secrets/youtube-oauth-client.json"), cfg.path("youtube.token", "secrets/youtube-token.json")
    c = InstalledAppFlow.from_client_secrets_file(str(secret), SCOPES).run_local_server(port=0, prompt="select_account consent")
    token.parent.mkdir(parents=True, exist_ok=True)
    token.write_text(c.to_json())
    token.chmod(0o600)
    return token


def _service(cfg):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    build, _, _ = _libs()
    token = cfg.path("youtube.token", "secrets/youtube-token.json")
    if not token.exists():
        raise ConfigError(f"no YouTube token at {token}: run `autopilot youtube-auth`")
    c = Credentials.from_authorized_user_file(str(token))   # its own stored scopes: older tokens keep working
    if c.expired and c.refresh_token:
        c.refresh(Request())
        token.write_text(c.to_json())
    return build("youtube", "v3", credentials=c, cache_discovery=False)


def _upload(ctx, item, short: bool):
    _, HttpError, MediaFileUpload = _libs()
    yt = _service(ctx.cfg)
    desc = item.description or item.caption
    if short and "#shorts" not in desc.lower():
        desc = (desc + "\n\n#Shorts").strip()
    body = {"snippet": {"title": (item.title or item.slug)[:100], "description": desc[:5000], "tags": item.tags,
                        "categoryId": str(ctx.cfg.get("youtube.category", "22")), "defaultLanguage": item.language,
                        "defaultAudioLanguage": item.language},
            "status": {"privacyStatus": ctx.cfg.get("youtube.privacy", "public"), "selfDeclaredMadeForKids": False,
                       "embeddable": True, "publicStatsViewable": True}}
    if item.publish_at:   # scheduled release: uploaded private, YouTube makes it public at that time
        body["status"]["privacyStatus"] = "private"
        body["status"]["publishAt"] = item.publish_at
    try:
        req = yt.videos().insert(part="snippet,status", body=body,
                                 media_body=MediaFileUpload(str(item.files["video"]), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True))
        resp = None
        while resp is None:
            _, resp = req.next_chunk()
        vid = resp["id"]
        if item.files.get("thumbnail") and not short:
            try:
                yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(item.files["thumbnail"]))).execute()
            except HttpError:
                pass  # a thumbnail problem must not undo a published video
        if item.comment:
            try:
                yt.commentThreads().insert(part="snippet", body={"snippet": {"videoId": vid, "topLevelComment": {
                    "snippet": {"textOriginal": item.comment}}}}).execute()
            except HttpError:
                pass  # comments may be off for the channel; never undo the upload for it
        if item.playlist:
            yt.playlistItems().insert(part="snippet", body={"snippet": {"playlistId": item.playlist,
                                      "resourceId": {"kind": "youtube#video", "videoId": vid}}}).execute()
    except HttpError as e:
        if b"uploadLimitExceeded" in e.content or b"quotaExceeded" in e.content:
            raise QuotaReached("YouTube upload limit reached for today") from None
        raise AutopilotError(f"YouTube upload failed: {e}") from None
    return Result(url=(f"https://youtube.com/shorts/{vid}" if short else f"https://youtube.com/watch?v={vid}"), remote_id=vid)


def short(ctx, item):
    return _upload(ctx, item, True)


def video(ctx, item):
    return _upload(ctx, item, False)
