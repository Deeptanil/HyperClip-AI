"""
YouTube Shorts Uploader using YouTube Data API v3.
Runs completely free with standard OAuth2 credentials.
"""

import os
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

def upload_short(
    video_path,
    title,
    description=None,
    tags=None,
    privacy="public",
    client=None,
    category_id="23",
    title_suffix="#Shorts",
):
    """
    Uploads a vertical video as a YouTube Short.
    Adding #Shorts in title and description ensures YouTube indexes it into the Shorts feed.
    """
    if client is None:
        client = get_youtube_client()

    full_title = f"{title} {title_suffix}".strip() if title_suffix else title
    full_desc = description or f"{title}\n\n#Shorts #viral"
    default_tags = list(tags) if tags else ["shorts", "viral", "clips"]

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")
    
    body = {
        "snippet": {
            "title": full_title[:100],
            "description": full_desc,
            "tags": default_tags,
            "categoryId": str(category_id)
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False
        }
    }

    print(f"[*] Uploading '{video_path}' to YouTube Shorts...")
    request = client.videos().insert(part="snippet,status", body=body, media_body=media)
    response = request.execute()
    video_id = response.get("id")
    video_url = f"https://youtube.com/shorts/{video_id}"
    print(f"[+] Uploaded successfully: {video_url}")
    return video_url
