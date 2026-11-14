"""
Instagram Reels Uploader.
Supports:
1. Meta Graph API (Official Developer API - Abhinavkumar-07 style)
2. Direct Upload via instagrapi (Local direct upload without needing public URL)
"""

import os
import time
import requests

def upload_reel_meta_graph(video_url, caption, ig_user_id=None, access_token=None):
    """
    Uploads a reel via Meta Graph API (Official).
    Requires:
      - video_url: Publicly accessible URL (Google Drive / GitHub release / Cloudinary)
      - ig_user_id: Instagram Business/Creator Account ID
      - access_token: Long-lived Meta User/Page Access Token
    """
    ig_user_id = ig_user_id or os.getenv("INSTAGRAM_ACCOUNT_ID")
    access_token = access_token or os.getenv("META_ACCESS_TOKEN")

    if not all([ig_user_id, access_token]):
        raise ValueError("Missing Instagram Graph API credentials (INSTAGRAM_ACCOUNT_ID, META_ACCESS_TOKEN).")

    print("[*] Creating Instagram Reel media container...")
    container_endpoint = f"https://graph.facebook.com/v20.0/{ig_user_id}/media"
    payload = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": access_token
    }

    res = requests.post(container_endpoint, data=payload).json()
    if "id" not in res:
        raise RuntimeError(f"Failed to create Instagram container: {res}")

    creation_id = res["id"]

    # Wait for Instagram video processing
    status_endpoint = f"https://graph.facebook.com/v20.0/{creation_id}"
    print("[*] Waiting for Instagram video processing...")
    for _ in range(30):
        time.sleep(5)
        check = requests.get(status_endpoint, params={"fields": "status_code", "access_token": access_token}).json()
        status = check.get("status_code")
        if status == "FINISHED":
            break
        elif status == "ERROR":
            raise RuntimeError(f"Instagram video processing failed: {check}")

    # Publish the container
    print("[*] Publishing Reel...")
    publish_endpoint = f"https://graph.facebook.com/v20.0/{ig_user_id}/media_publish"
    pub_res = requests.post(publish_endpoint, data={"creation_id": creation_id, "access_token": access_token}).json()
    reel_id = pub_res.get("id")
    print(f"[+] Published Instagram Reel ID: {reel_id}")
    return reel_id

def upload_reel_direct(video_path, caption, username=None, password=None):
    """
    Direct upload using instagrapi without needing a public web URL.
    """
    try:
        from instagrapi import Client
    except ImportError:
        raise ImportError("instagrapi is required for direct upload. Run: pip install instagrapi")

    username = username or os.getenv("INSTA_USERNAME")
    password = password or os.getenv("INSTA_PASSWORD")

    if not all([username, password]):
        raise ValueError("Missing INSTA_USERNAME or INSTA_PASSWORD.")

    print(f"[*] Logging into Instagram as {username}...")
    cl = Client()
    cl.login(username, password)
    
    print(f"[*] Uploading reel: {video_path}...")
    media = cl.clip_upload(video_path, caption=caption)
    print(f"[+] Uploaded Instagram Reel: https://instagram.com/reel/{media.code}")
    return media.code
