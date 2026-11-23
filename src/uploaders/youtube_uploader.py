"""
YouTube Shorts Uploader using YouTube Data API v3.
Runs completely free with standard OAuth2 credentials.
"""

import os
import re
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def get_youtube_client(client_id=None, client_secret=None, refresh_token=None):
    """Initializes YouTube API client using OAuth credentials."""
    client_id = client_id or os.getenv("YOUTUBE_CLIENT_ID")
    client_secret = client_secret or os.getenv("YOUTUBE_CLIENT_SECRET")
    refresh_token = refresh_token or os.getenv("YOUTUBE_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        raise ValueError("Missing YouTube OAuth credentials (CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN).")

    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES
    )
    credentials.refresh(Request())
    return build("youtube", "v3", credentials=credentials)

def get_optimal_publish_time(
    existing_timestamps: list = None,
    now: datetime = None,
    shorts_per_day: int = 4,
    min_gap_hours: float = 2.5,
    max_scheduled_ahead: int = 1,
    force: bool = False,
) -> tuple[bool, str | None, str]:
    """
    Determines whether a YouTube Short should be published immediately
    or scheduled for the next optimal peak audience window via publishAt.
    
    Decouples YouTube releases from GitHub Actions cron jitter and delays.
    Peak US/Global English gaming audience windows (UTC):
      4 posts/day -> 15:00, 17:30, 20:00, 22:30 UTC (10 AM to 6:30 PM EDT)
      3 posts/day -> 16:30, 19:30, 22:30 UTC
      2 posts/day -> 16:30, 21:00 UTC
      
    Returns:
      (can_post: bool, publish_at_iso_or_none: str | None, reason: str)
    """
    if force:
        return True, None, "Force mode enabled: publishing immediately"

    now = now or datetime.now(timezone.utc)
    if not now.tzinfo:
        now = now.replace(tzinfo=timezone.utc)

    # Define peak slots based on target daily posts
    if shorts_per_day >= 4:
        slots = [(15, 0), (17, 30), (20, 0), (22, 30)]
    elif shorts_per_day == 3:
        slots = [(16, 30), (19, 30), (22, 30)]
    elif shorts_per_day == 2:
        slots = [(16, 30), (21, 0)]
    else:
        slots = [(18, 0)]

    existing = []
    for ts in (existing_timestamps or []):
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                continue
        if isinstance(ts, datetime):
            if not ts.tzinfo:
                ts = ts.replace(tzinfo=timezone.utc)
            else:
                ts = ts.astimezone(timezone.utc)
            existing.append(ts)

    existing_today = [ts for ts in existing if ts.date() == now.date()]

    # Limit how many future scheduled posts are queued up at once
    future_scheduled = [ts for ts in existing_today if ts > now]
    if len(future_scheduled) >= max_scheduled_ahead:
        sched_time_str = future_scheduled[0].strftime("%H:%M UTC")
        return False, None, f"Upcoming Short already scheduled ahead for {sched_time_str}"

    # Check if current time is inside prime viewing hours (14:30 - 23:00 UTC)
    in_peak = (14 <= now.hour <= 22) or (now.hour == 14 and now.minute >= 30) or (now.hour == 23 and now.minute == 0)
    past_posts = [ts for ts in existing_today if ts <= now]
    last_post = max(past_posts) if past_posts else None
    cooldown_ok = (last_post is None) or ((now - last_post).total_seconds() >= min_gap_hours * 3600)

    if in_peak and cooldown_ok and not future_scheduled:
        return True, None, "Peak viewing window active and cooldown satisfied: publishing immediately"

    # Outside peak hours or recent post cooldown active -> Schedule for next open peak slot today
    for h, m in slots:
        slot_dt = now.replace(hour=h, minute=m, second=0, microsecond=0)
        # Must be at least 10 minutes in the future for YouTube API
        if slot_dt > now + timedelta(minutes=10):
            conflict = False
            for ts in existing_today:
                if abs((slot_dt - ts).total_seconds()) < (min_gap_hours - 0.5) * 3600:
                    conflict = True
                    break
            if not conflict:
                iso_val = slot_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                return True, iso_val, f"Off-peak/cooldown active; scheduled for prime peak slot at {h:02d}:{m:02d} UTC"

    return False, None, "All prime peak slots for today are occupied"

def format_shorts_title(raw_title: str, streamer: str = None, hook_prefix: str = None) -> str:
    """
    Enforces streamer name and high-CTR hook formatting for YouTube Shorts discovery.
    Formats: 'STREAMER: [HOOK] [EMOJI]' (truncated so title + ' #Shorts' <= 100 chars).
    Avoids duplicate streamer prefixes if the name is already present (e.g. 'Kai Cenat' vs 'kaicenat').
    """
    clean_title = (raw_title or "").strip()
    # Remove existing #Shorts or other hashtags from raw title to avoid duplication
    clean_title = re.sub(r'#\w+', '', clean_title).strip()

    streamer_clean = (streamer or "").strip()
    if streamer_clean:
        streamer_norm = re.sub(r'[^a-zA-Z0-9]', '', streamer_clean).lower()
        title_norm = re.sub(r'[^a-zA-Z0-9]', '', clean_title).lower()
        if streamer_norm and streamer_norm not in title_norm:
            clean_title = f"{streamer_clean.upper()}: {clean_title}"

    # Ensure length <= 88 chars so ' #Shorts' fits comfortably under YouTube's 100-char limit
    if len(clean_title) > 88:
        clean_title = clean_title[:85].rstrip() + "..."

    return clean_title

def upload_short(
    video_path,
    title,
    description=None,
    tags=None,
    privacy="public",
    client=None,
    category_id="20",
    title_suffix="#Shorts",
    publish_at: str = None,
    streamer: str = None,
):
    """
    Uploads a vertical video as a YouTube Short.
    Adding #Shorts in title and description ensures YouTube indexes it into the Shorts feed.
    If publish_at (ISO 8601 string, e.g. '2026-11-24T17:30:00Z') is provided,
    YouTube schedules the video privately and publishes it automatically at that exact time.
    Category 20 = Gaming.
    """
    if client is None:
        client = get_youtube_client()

    formatted_title = format_shorts_title(title, streamer=streamer)
    full_title = f"{formatted_title} {title_suffix}".strip() if title_suffix else formatted_title
    full_desc = description or f"{formatted_title}\n\n#Shorts #gaming #twitch #viral"
    default_tags = list(tags) if tags else ["shorts", "gaming", "twitch", "viral", "clips"]

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")

    status_dict = {
        "privacyStatus": "private" if publish_at else privacy,
        "selfDeclaredMadeForKids": False
    }
    if publish_at:
        status_dict["publishAt"] = publish_at

    body = {
        "snippet": {
            "title": full_title[:100],
            "description": full_desc,
            "tags": default_tags,
            "categoryId": str(category_id)
        },
        "status": status_dict
    }

    sched_label = f" [Scheduled publishAt: {publish_at}]" if publish_at else ""
    print(f"[*] Uploading '{video_path}' to YouTube Shorts{sched_label}...")
    request = client.videos().insert(part="snippet,status", body=body, media_body=media)
    response = request.execute()
    video_id = response.get("id")
    video_url = f"https://youtube.com/shorts/{video_id}"
    print(f"[+] Uploaded successfully{' (Scheduled)' if publish_at else ''}: {video_url}")
    return video_url
