"""
Autonomous Storytelling Pipeline & Multi-Platform Auto Poster.
Runs 2 times daily (every 12 hours) on GitHub Actions.
Maintains:
  - output/pipeline/: Staged next video ready for release.
  - output/posted/: Archive of the last 7 days of published videos (auto-pruned).
"""

import os
import sys
import json
import re
import shutil
import asyncio
import argparse
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(__file__))

from src.uploaders.youtube_uploader import upload_short
from src.uploaders.instagram_uploader import upload_reel_direct, upload_reel_meta_graph
from src.uploaders.tiktok_uploader import upload_tiktok
from generate_story import build_story_video

LOG_FILE = "posted_log.json"
OUTPUT_DIR = "output"
PIPELINE_DIR = os.path.join(OUTPUT_DIR, "pipeline")
POSTED_DIR = os.path.join(OUTPUT_DIR, "posted")

def ensure_directories():
    os.makedirs(PIPELINE_DIR, exist_ok=True)
    os.makedirs(POSTED_DIR, exist_ok=True)

def slugify(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '_', text).strip('_')
    return text[:28]

def load_log():
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_log_entry(entry):
    logs = load_log()
    logs.append(entry)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)

def prune_posted_archive(days=7):
    """Deletes posted videos older than 7 days to keep repository lean."""
    ensure_directories()
    now = datetime.utcnow()
    cutoff = now - timedelta(days=days)
    
    for fname in os.listdir(POSTED_DIR):
        if not fname.endswith((".mp4", ".json")):
            continue
        fpath = os.path.join(POSTED_DIR, fname)
        is_pruned = False
        
        # Check filename prefix YYYY-MM-DD
        match = re.match(r"^(\d{4}-\d{2}-\d{2})", fname)
        if match:
            try:
                f_date = datetime.strptime(match.group(1), "%Y-%m-%d")
                if f_date < cutoff:
                    os.remove(fpath)
                    print(f"[*] Pruned expired archive (>7 days): {fname}")
                    is_pruned = True
            except Exception:
                pass
                
        if not is_pruned:
            mtime = datetime.utcfromtimestamp(os.path.getmtime(fpath))
            if mtime < cutoff:
                os.remove(fpath)
                print(f"[*] Pruned expired archive by mtime (>7 days): {fname}")

def get_queued_videos():
    """Returns sorted list of videos waiting in output/pipeline/."""
    ensure_directories()
    files = sorted([f for f in os.listdir(PIPELINE_DIR) if f.endswith(".mp4")])
    return [os.path.join(PIPELINE_DIR, f) for f in files]

async def stage_new_video(category=None, topic=None, style_mode="historical_cartoon"):
    """Generates a new story video and stages it in output/pipeline/."""
    ensure_directories()
    categories = ["history", "mythology", "humor"]
    if not category:
        # Rotate category based on log history
        logs = load_log()
        last_cat = logs[-1].get("category", "") if logs else ""
        next_cats = [c for c in categories if c != last_cat]
        category = next_cats[0] if next_cats else "history"

    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    temp_target = os.path.join(PIPELINE_DIR, f"temp_{date_str}.mp4")

    print(f"\n[*] Staging new {category} video into pipeline...")
    rendered_mp4 = await build_story_video(
        category=category,
        topic=topic,
        style_mode=style_mode,
        output_path=temp_target,
        publish=False
    )

    # Derive short title and metadata
    from src.story_engine.vault import STORY_VAULT
    matching = [s for s in STORY_VAULT if s["category"] == category]
    story_meta = matching[0] if matching else {"title": f"{category.capitalize()} Story"}
    
    title = story_meta.get("title", f"{category.capitalize()} Story")
    short_slug = slugify(title)
    final_video_name = f"{date_str}-{short_slug}.mp4"
    final_video_path = os.path.join(PIPELINE_DIR, final_video_name)
    
    # Avoid collision if file exists
    count = 1
    while os.path.exists(final_video_path):
        final_video_name = f"{date_str}-{short_slug}_{count}.mp4"
        final_video_path = os.path.join(PIPELINE_DIR, final_video_name)
        count += 1

    shutil.move(rendered_mp4, final_video_path)

    # Write companion metadata json
    meta_json_path = os.path.splitext(final_video_path)[0] + ".json"
    tags = f"#{category} #history #animation #storytime #shorts #reels"
    meta_data = {
        "title": f"{title} 🎬",
        "category": category,
        "caption": f"{title}\n\n{story_meta.get('hook', '')}\n\n{tags}",
        "staged_at": datetime.utcnow().isoformat()
    }
    with open(meta_json_path, "w", encoding="utf-8") as f:
        json.dump(meta_data, f, indent=2)

    print(f"[+] Successfully staged video: {final_video_path}")
    return final_video_path, meta_data

async def run_pipeline(platforms=None):
    if platforms is None:
        platforms = ["youtube", "instagram"]

    ensure_directories()
    prune_posted_archive(days=7)

    queued = get_queued_videos()
    
    # If pipeline is completely empty, stage a video right now
    if not queued:
        print("[*] Pipeline empty. Staging an initial video...")
        new_video, _ = await stage_new_video()
        queued = [new_video]

    # Select the first video in the pipeline to post
    video_to_post = queued[0]
    json_path = os.path.splitext(video_to_post)[0] + ".json"
    meta = {}
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            pass

    title = meta.get("title", os.path.basename(video_to_post).replace(".mp4", "").replace("-", " ").title())
    caption = meta.get("caption", f"{title} #shorts #animation #storytime #reels")

    print("\n" + "=" * 60)
    print(f"🚀 PUBLISHING PIPELINE VIDEO: {video_to_post}")
    print(f"📌 TITLE:   {title}")
    print(f"🌐 TARGETS: {platforms}")
    print("=" * 60)

    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "video": os.path.basename(video_to_post),
        "title": title,
        "category": meta.get("category", "story"),
        "uploads": {}
    }

    # 1. YouTube Shorts Upload
    if "youtube" in platforms:
        try:
            print("\n[*] Uploading to YouTube Shorts...")
            yt_url = upload_short(video_to_post, title=title, description=caption)
            results["uploads"]["youtube"] = yt_url
            print(f"[+] YouTube live: {yt_url}")
        except Exception as e:
            print(f"[-] YouTube upload error: {e}")
            results["uploads"]["youtube"] = f"Failed: {e}"

    # 2. Instagram Reels Upload
    if "instagram" in platforms:
        try:
            print("\n[*] Uploading to Instagram Reels...")
            if os.getenv("META_ACCESS_TOKEN") and os.getenv("VIDEO_PUBLIC_URL"):
                ig_id = upload_reel_meta_graph(os.getenv("VIDEO_PUBLIC_URL"), caption)
                results["uploads"]["instagram"] = f"Meta Reel ID: {ig_id}"
            elif os.getenv("INSTA_USERNAME") and os.getenv("INSTA_PASSWORD"):
                code = upload_reel_direct(video_to_post, caption)
                results["uploads"]["instagram"] = f"https://instagram.com/reel/{code}"
                print(f"[+] Instagram live: https://instagram.com/reel/{code}")
            else:
                print("[!] Instagram credentials not provided. Skipping Instagram.")
        except Exception as e:
            print(f"[-] Instagram upload error: {e}")
            results["uploads"]["instagram"] = f"Failed: {e}"

    # 3. TikTok (Optional)
    if "tiktok" in platforms:
        try:
            status = upload_tiktok(video_to_post, description=caption)
            results["uploads"]["tiktok"] = "Success" if status else "Skipped"
        except Exception as e:
            results["uploads"]["tiktok"] = f"Failed: {e}"

    save_log_entry(results)

    # Move posted video and metadata to output/posted/
    posted_dest_mp4 = os.path.join(POSTED_DIR, os.path.basename(video_to_post))
    shutil.move(video_to_post, posted_dest_mp4)
    if os.path.exists(json_path):
        shutil.move(json_path, os.path.join(POSTED_DIR, os.path.basename(json_path)))
    print(f"[+] Archived posted video to: {posted_dest_mp4}")

    # Ensure pipeline has the NEXT video staged and ready
    remaining = get_queued_videos()
    if not remaining:
        print("\n[*] Staging the NEXT post into pipeline for subsequent run...")
        await stage_new_video()
    else:
        print(f"[+] Next post already waiting in pipeline: {remaining[0]}")

    print("\n" + "=" * 60)
    print("✅ RUN COMPLETED SUCCESSFULLY")
    print("=" * 60)
    return results

def main():
    parser = argparse.ArgumentParser(description="Autonomous Storytelling Pipeline & Publisher")
    parser.add_argument("--platforms", nargs="+", choices=["youtube", "instagram", "tiktok"], default=["youtube", "instagram"])
    parser.add_argument("--stage-only", action="store_true", help="Stage a new video in pipeline without publishing")
    args = parser.parse_args()

    if args.stage_only:
        asyncio.run(stage_new_video())
    else:
        asyncio.run(run_pipeline(platforms=args.platforms))

if __name__ == "__main__":
    main()
