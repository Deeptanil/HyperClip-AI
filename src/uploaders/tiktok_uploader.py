"""
TikTok Uploader using Playwright and session cookies.
Bypasses login forms and captcha gates by reusing active browser session cookies.
"""

import os
import subprocess

def upload_tiktok(video_path, description, cookies_file=None):
    """
    Uploads video to TikTok using tiktok-uploader CLI / Playwright.
    Requires cookies.txt extracted once from logged-in browser session.
    """
    cookies_file = cookies_file or os.getenv("TIKTOK_COOKIES_PATH", "cookies.txt")

    if not os.path.exists(cookies_file):
        print(f"[!] TikTok cookies file '{cookies_file}' not found. Skipping TikTok upload.")
        return None

    cmd = [
        "tiktok-uploader",
        "-v", video_path,
        "-d", description,
        "-c", cookies_file
    ]

    print(f"[*] Uploading '{video_path}' to TikTok...")
    try:
        subprocess.run(cmd, check=True)
        print("[+] TikTok upload initiated successfully.")
        return True
    except Exception as e:
        print(f"[-] TikTok upload failed: {e}")
        return False
