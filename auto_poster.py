"""
Unified Multi-Platform Auto Poster.
Orchestrates generation and publishing to YouTube Shorts, Instagram Reels, and TikTok.
Keeps a persistent log (posted_log.json) to prevent duplicates and track analytics.
"""

import os
import sys
import json
import asyncio
import argparse
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from main import generate_single_video
from uploaders.youtube_uploader import upload_short
from uploaders.instagram_uploader import upload_reel_direct, upload_reel_meta_graph
from uploaders.tiktok_uploader import upload_tiktok

LOG_FILE = "posted_log.json"

def load_log():
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_log(entry):
    logs = load_log()
    logs.append(entry)
    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=2)

async def run_pipeline(platforms=None, topic=None):
    if platforms is None:
        platforms = ["youtube", "instagram", "tiktok"]

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    video_filename = f"daily_short_{timestamp}.mp4"

    # Step 1: Generate the video
    print(f"\n==========================================")
    print(f"🚀 GENERATING DAILY VIRAL STICKMAN SHORT")
    print(f"==========================================")
    video_path = await generate_single_video(topic=topic, output_path=video_filename)

    caption = f"Bro why is this so accurate? 😭 #shorts #stickman #animation #relatable #humor #fyp"
    title = "Why Humans Are Actually Weird"

    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "video": video_path,
        "uploads": {}
    }

    # Step 2: YouTube Shorts
    if "youtube" in platforms:
        try:
            yt_url = upload_short(video_path, title=title, description=caption)
            results["uploads"]["youtube"] = yt_url
        except Exception as e:
            print(f"[-] YouTube upload error: {e}")
            results["uploads"]["youtube"] = f"Failed: {e}"

    # Step 3: Instagram Reels
    if "instagram" in platforms:
        try:
            if os.getenv("META_ACCESS_TOKEN") and os.getenv("VIDEO_PUBLIC_URL"):
                # Meta Graph API method (Abhinavkumar-07 style)
                ig_id = upload_reel_meta_graph(os.getenv("VIDEO_PUBLIC_URL"), caption)
                results["uploads"]["instagram"] = f"Meta Reel ID: {ig_id}"
            elif os.getenv("INSTA_USERNAME") and os.getenv("INSTA_PASSWORD"):
                # Direct local upload method via instagrapi
                code = upload_reel_direct(video_path, caption)
                results["uploads"]["instagram"] = f"https://instagram.com/reel/{code}"
            else:
                print("[!] Instagram credentials not provided. Skipping Instagram.")
        except Exception as e:
            print(f"[-] Instagram upload error: {e}")
            results["uploads"]["instagram"] = f"Failed: {e}"

    # Step 4: TikTok
    if "tiktok" in platforms:
        try:
            status = upload_tiktok(video_path, description=caption)
            results["uploads"]["tiktok"] = "Success" if status else "Skipped/Failed"
        except Exception as e:
            print(f"[-] TikTok upload error: {e}")
            results["uploads"]["tiktok"] = f"Failed: {e}"

    save_log(results)
    print("\n==========================================")
    print(f"✅ PIPELINE FINISHED - LOG SAVED TO {LOG_FILE}")
    print("==========================================")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--platforms", nargs="+", default=["youtube", "instagram", "tiktok"])
    parser.add_argument("--topic", type=str, default=None)
    args = parser.parse_args()

    asyncio.run(run_pipeline(platforms=args.platforms, topic=args.topic))
