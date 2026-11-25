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

def upload_reel_meta_graph(video_path_or_url: str, caption: str, account_slot: int = 1, ig_user_id: str = None, access_token: str = None, scheduled_publish_time: int = None) -> tuple[str, str]:
    """
    Uploads a reel via the official Meta Graph API (Zero-bot challenge / shadowban immune).
    Supports:
      1. Local files via Resumable Upload (rupload.facebook.com) - no public URL needed!
      2. Publicly accessible URLs.
      3. Native Meta Graph scheduling via scheduled_publish_time (Unix timestamp).
    Returns (media_id, permalink_or_url).
    """
    token = access_token or os.getenv("META_ACCESS_TOKEN")
    if account_slot == 2:
        user_id = ig_user_id or os.getenv("INSTAGRAM_ACCOUNT_ID_2") or os.getenv("INSTAGRAM_ACCOUNT_ID")
    else:
        user_id = ig_user_id or os.getenv("INSTAGRAM_ACCOUNT_ID")

    if not all([user_id, token]):
        raise ValueError("Missing Meta Graph API credentials (INSTAGRAM_ACCOUNT_ID / META_ACCESS_TOKEN).")

    is_local_file = os.path.exists(video_path_or_url)
    api_ver = "v21.0"
    base_graph = f"https://graph.facebook.com/{api_ver}"

    sched_info = f" [Scheduled publish time: {scheduled_publish_time}]" if scheduled_publish_time else ""
    print(f"[*] Initializing Meta Graph API Reel container (Slot {account_slot}, Account ID {user_id}){sched_info}...")
    container_endpoint = f"{base_graph}/{user_id}/media"

    if is_local_file:
        file_size = os.path.getsize(video_path_or_url)
        payload = {
            "media_type": "REELS",
            "upload_type": "resumable",
            "caption": caption,
            "access_token": token,
        }
        if scheduled_publish_time:
            payload["scheduled_publish_time"] = int(scheduled_publish_time)
        res = requests.post(container_endpoint, data=payload, timeout=30).json()
        if "id" not in res:
            raise RuntimeError(f"Failed to create Instagram resumable container: {res}")

        creation_id = res["id"]
        upload_uri = res.get("uri") or f"https://rupload.facebook.com/ig-api-upload/{api_ver}/{creation_id}"

        print(f"[*] Uploading binary video file ({file_size / (1024*1024):.2f} MB) to Meta Ruploader...")
        upload_headers = {
            "Authorization": f"OAuth {token}",
            "offset": "0",
            "file_size": str(file_size),
            "Content-Type": "application/octet-stream",
        }
        with open(video_path_or_url, "rb") as f:
            up_res = requests.post(upload_uri, headers=upload_headers, data=f, timeout=180)
            if up_res.status_code not in (200, 201):
                raise RuntimeError(f"Resumable video upload failed ({up_res.status_code}): {up_res.text}")
    else:
        payload = {
            "media_type": "REELS",
            "video_url": video_path_or_url,
            "caption": caption,
            "access_token": token,
        }
        if scheduled_publish_time:
            payload["scheduled_publish_time"] = int(scheduled_publish_time)
        res = requests.post(container_endpoint, data=payload, timeout=30).json()
        if "id" not in res:
            raise RuntimeError(f"Failed to create Instagram container: {res}")
        creation_id = res["id"]

    # Poll status
    status_endpoint = f"{base_graph}/{creation_id}"
    print(f"[*] Waiting for Instagram to process video container ({creation_id})...")
    finished = False
    last_status = None
    for attempt in range(40):
        time.sleep(5)
        check = requests.get(status_endpoint, params={"fields": "status_code", "access_token": token}, timeout=15).json()
        last_status = check.get("status_code")
        print(f"    Container status: {last_status} (check {attempt+1}/40)")
        if last_status == "FINISHED":
            finished = True
            break
        elif last_status in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram video processing failed ({last_status}): {check}")
    if not finished:
        raise RuntimeError(f"Instagram video processing timed out after 200s (last status: {last_status})")

    if scheduled_publish_time:
        print(f"[+] Successfully scheduled Instagram Reel container {creation_id} for {scheduled_publish_time} on Meta Graph API.")
        return creation_id, f"https://instagram.com/reel/{creation_id}"

    # Publish container
    print(f"[*] Publishing media container ({creation_id}) to Instagram...")
    pub_res = requests.post(
        f"{base_graph}/{user_id}/media_publish",
        data={"creation_id": creation_id, "access_token": token},
        timeout=30
    ).json()

    if "id" not in pub_res:
        raise RuntimeError(f"Failed to publish Instagram container: {pub_res}")

    media_id = pub_res["id"]
    permalink = f"https://instagram.com/reel/{media_id}"
    try:
        media_info = requests.get(f"{base_graph}/{media_id}", params={"fields": "permalink", "access_token": token}, timeout=10).json()
        if media_info.get("permalink"):
            permalink = media_info["permalink"]
    except Exception:
        pass

    print(f"[+] Published Official Meta Instagram Reel: {permalink} (ID: {media_id})")
    return media_id, permalink


def upload_reel(video_path: str, caption: str, account_slot: int = 1, trial: bool = False, scheduled_publish_time: int = None, **kwargs) -> str:
    """
    Smart hybrid Instagram Reel uploader:
    1. Primary: Official Meta Graph API for standard public reels (resumable local file upload) - Zero bot blocks.
    2. Trial Reels & Direct Fallback: instagrapi session-based uploader (Meta Graph API does not support Trial Reels).
    """
    token = os.getenv("META_ACCESS_TOKEN")
    ig_id = os.getenv("INSTAGRAM_ACCOUNT_ID_2" if account_slot == 2 else "INSTAGRAM_ACCOUNT_ID")
    if not trial and token and ig_id:
        try:
            _, permalink = upload_reel_meta_graph(
                video_path,
                caption,
                account_slot=account_slot,
                scheduled_publish_time=scheduled_publish_time,
            )
            return permalink
        except Exception as e:
            print(f"[!] Meta Graph API upload attempt failed ({e}). Falling back to direct session...")

    code = upload_reel_direct(video_path, caption, account_slot=account_slot, trial=trial)
    return f"https://instagram.com/reel/{code}"

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
    challenge_code = challenge_code or os.getenv(f"INSTA_VERIFICATION_CODE{suffix}", os.getenv("INSTA_VERIFICATION_CODE", ""))

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
        try:
            media = cl.clip_upload(video_path, **upload_kwargs)
        except TypeError:
            # Older instagrapi versions without trial kwargs
            for k in ("trial", "trial_graduation_strategy", "show_preview_in_feed"):
                upload_kwargs.pop(k, None)
            use_trial = False
            media = cl.clip_upload(video_path, **upload_kwargs)
        except Exception as trial_err:
            if use_trial and ("trial" in str(trial_err).lower() or "eligible" in str(trial_err).lower()):
                print(f"[!] Trial Reel rejected by Instagram ({trial_err}); falling back to Regular Reel...")
                for k in ("trial", "trial_graduation_strategy", "show_preview_in_feed"):
                    upload_kwargs.pop(k, None)
                use_trial = False
                media = cl.clip_upload(video_path, **upload_kwargs)
            else:
                raise
    finally:
        if thumb_path and os.path.exists(thumb_path):
            try:
                os.remove(thumb_path)
            except Exception:
                pass

    reel_url = f"https://instagram.com/reel/{media.code}"
    print(f"[+] Uploaded Instagram {'Trial ' if use_trial else ''}Reel: {reel_url}")
    return media.code
