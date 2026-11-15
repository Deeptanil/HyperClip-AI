"""
Instagram Reels Uploader.
Supports:
1. Meta Graph API (Official Developer API - Abhinavkumar-07 style)
2. Direct Upload via instagrapi (with session persistence & challenge code resolution)
"""

import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

SESSION_FILE = "ig_session.json"

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

def upload_reel_direct(video_path, caption, username=None, password=None, challenge_code=None, account_slot=1, trial=False):
    """
    Direct upload using instagrapi without needing a public web URL.
    Reuses session cookies to bypass repeated 2FA/checkpoint security checks.
    Supports account_slot=1 (primary) and account_slot=2 (secondary clip account),
    and Trial Reels (trial=True) with automatic eligibility check.
    """
    try:
        from instagrapi import Client
    except ImportError:
        raise ImportError("instagrapi is required for direct upload. Run: pip install instagrapi")

    suffix = "" if account_slot == 1 else f"_{account_slot}"
    session_file = SESSION_FILE if account_slot == 1 else f"ig_session_{account_slot}.json"

    username = username or os.getenv(f"INSTA_USERNAME{suffix}")
    password = password or os.getenv(f"INSTA_PASSWORD{suffix}")
    challenge_code = challenge_code or os.getenv(f"INSTA_VERIFICATION_CODE{suffix}", os.getenv("INSTA_VERIFICATION_CODE", "449932"))

    if not all([username, password]):
        raise ValueError(f"Missing INSTA_USERNAME{suffix} or INSTA_PASSWORD{suffix}.")

    cl = Client()

    def challenge_code_handler(user, choice):
        print(f"[*] Instagram challenge requested ({choice}). Submitting verification code: {challenge_code}")
        return str(challenge_code).strip()

    cl.challenge_code_handler = challenge_code_handler

    # 1. Restore session from secret or file if available
    session_data = os.getenv(f"INSTA_SESSION_DATA{suffix}")
    if session_data and not os.path.exists(session_file):
        try:
            with open(session_file, "w", encoding="utf-8") as f:
                f.write(session_data)
            print(f"[+] Restored session from INSTA_SESSION_DATA{suffix} environment variable")
        except Exception:
            pass

    logged_in = False
    if os.path.exists(session_file):
        try:
            print(f"[*] Reusing saved session from {session_file}...")
            cl.load_settings(session_file)
            cl.login(username, password)
            logged_in = True
        except Exception as e:
            print(f"[!] Session reuse failed ({e}), logging in fresh...")

    # 2. Fresh login with challenge handler
    if not logged_in:
        print(f"[*] Logging into Instagram (slot {account_slot}) as {username}...")
        cl.login(username, password)
        try:
            cl.dump_settings(session_file)
            print(f"[+] Saved fresh session to {session_file}")
        except Exception:
            pass

    # Generate custom thumbnail with FFmpeg so moviepy is not required
    thumb_path = os.path.splitext(video_path)[0] + "_thumb.jpg"
    try:
        import subprocess
        cmd_thumb = ["ffmpeg", "-y", "-ss", "00:00:02.000", "-i", video_path, "-vframes", "1", "-q:v", "2", thumb_path]
        subprocess.run(cmd_thumb, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"[!] Thumbnail generation warning: {e}")
        thumb_path = None

    use_trial = False
    if trial:
        try:
            eligible = cl.clip_trial_eligible() if hasattr(cl, "clip_trial_eligible") else True
            if eligible:
                use_trial = True
                print("[*] Uploading as Instagram Trial Reel (slot %s)..." % account_slot)
            else:
                print("[!] Account slot %s not eligible for Trial Reels; falling back to Regular Reel." % account_slot)
        except Exception as e:
            print(f"[!] Trial Reel eligibility check warning ({e}); attempting regular upload.")

    upload_kwargs = {"caption": caption}
    if thumb_path and os.path.exists(thumb_path):
        upload_kwargs["thumbnail"] = thumb_path

    if use_trial:
        upload_kwargs.update({
            "trial": True,
            "trial_graduation_strategy": "manual",
            "show_preview_in_feed": False,
        })

    print(f"[*] Uploading reel (slot {account_slot}, trial={use_trial}): {video_path}...")
    try:
        media = cl.clip_upload(video_path, **upload_kwargs)
    except TypeError:
        # Older instagrapi versions without trial kwargs
        for k in ("trial", "trial_graduation_strategy", "show_preview_in_feed"):
            upload_kwargs.pop(k, None)
        media = cl.clip_upload(video_path, **upload_kwargs)

    if thumb_path and os.path.exists(thumb_path):
        try:
            os.remove(thumb_path)
        except Exception:
            pass

    reel_url = f"https://instagram.com/reel/{media.code}"
    print(f"[+] Uploaded Instagram {'Trial ' if use_trial else ''}Reel: {reel_url}")
    return media.code
