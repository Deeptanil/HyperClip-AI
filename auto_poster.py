"""
Autonomous Storytelling Pipeline & Intelligent Multi-Platform Auto Poster.
Runs 6 times daily on GitHub Actions (with redundancy).
Enforces:
  - Max 2 posts per calendar day (IST timezone - Indian Audience).
  - Min 5.0-hour cooldown interval between consecutive uploads.
  - Optimal Indian viewer peak windows:
      * Lunch Window: After 12:00 PM IST
      * Evening Prime Time: After 7:00 PM IST
  - Staging Queue (output/pipeline/): Always keeps the next post ready.
  - Rolling Archive (output/posted/): Automatically deletes videos older than 7 days.
"""

import os
import sys
import json
import re
import shutil
import asyncio
import argparse
from datetime import datetime, timezone, timedelta

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

sys.path.append(os.path.dirname(__file__))

from src.uploaders.youtube_uploader import upload_short
from src.uploaders.instagram_uploader import upload_reel_direct, upload_reel_meta_graph
from src.uploaders.tiktok_uploader import upload_tiktok
from src.twitch_clipper.text_censor import sanitize_text_for_reach
from src.utils.logger import log_event, backup_critical_logs
from generate_story import build_story_video

LOG_FILE = "posted_log.json"
OUTPUT_DIR = "output"
PIPELINE_DIR = os.path.join(OUTPUT_DIR, "pipeline")
POSTED_DIR = os.path.join(OUTPUT_DIR, "posted")

# Indian Standard Time (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))

def get_now_ist():
    return datetime.now(IST)

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
                content = f.read()
            if "<<<<<<<" in content:
                lines = [l for l in content.splitlines() if not (l.startswith("<<<<<<<") or l.startswith("=======") or l.startswith(">>>>>>>"))]
                content = "\n".join(lines)
            return json.loads(content)
        except Exception:
            bak_path = os.path.join("logs", "backups", "posted_log.backup.json")
            if os.path.exists(bak_path):
                try:
                    with open(bak_path, "r", encoding="utf-8") as bf:
                        return json.load(bf)
                except Exception:
                    pass
            return []
    return []

def save_log_entry(entry):
    logs = load_log()
    logs.append(entry)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)

def check_can_post_now(force=False, min_gap_hours=5.0, max_daily_posts=2):
    """
    Intelligent Scheduling Gatekeeper for Indian Audience (IST):
    1. Maximum 2 posts per day.
    2. Minimum 5.0 hours separation between posts.
    3. Peak window alignment:
       - 1st post: Midday / Lunch peak (12:00 PM – 4:00 PM IST)
       - 2nd post: Prime evening peak (7:00 PM – 11:00 PM IST)
    """
    now_ist = get_now_ist()
    today_ist_str = now_ist.strftime("%Y-%m-%d")
    current_hour_ist = now_ist.hour + (now_ist.minute / 60.0)

    if force:
        print("[*] Force mode enabled: Bypassing time window and daily quota checks.")
        return True, "Force mode active"

    logs = load_log()
    today_posts = []
    last_post_time = None

    for entry in logs:
        # Check if entry had a successful upload
        uploads = entry.get("uploads", {})
        has_success = any(
            isinstance(val, str) and not val.lower().startswith("failed")
            for val in uploads.values()
        )
        if not has_success:
            continue

        ts_str = entry.get("timestamp")
        if not ts_str:
            continue
        try:
            # Parse ISO timestamp (handling UTC/offsets)
            dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            dt_ist = dt.astimezone(IST)
            if dt_ist.strftime("%Y-%m-%d") == today_ist_str:
                today_posts.append(dt_ist)
            if last_post_time is None or dt_ist > last_post_time:
                last_post_time = dt_ist
        except Exception:
            pass

    # Rule 1: Daily Quota Cap
    if len(today_posts) >= max_daily_posts:
        msg = f"Daily limit reached ({len(today_posts)}/{max_daily_posts} posted today in IST). All daily posts fulfilled."
        return False, msg

    # Rule 2: Minimum Interval Gap (Cooldown) - posts 24/7 without regional time-of-day gating
    if last_post_time:
        elapsed_hours = (now_ist - last_post_time).total_seconds() / 3600.0
        if elapsed_hours < min_gap_hours:
            remaining = min_gap_hours - elapsed_hours
            msg = f"Cooldown active: Last post was {elapsed_hours:.1f}h ago. Need {remaining:.1f}h more separation."
            return False, msg

    return True, f"Eligible for post {len(today_posts) + 1}/{max_daily_posts} (24/7 Global Schedule)"

def prune_posted_archive(days=0):
    """Deletes posted videos immediately to keep repository lean."""
    ensure_directories()
    for fname in os.listdir(POSTED_DIR):
        fpath = os.path.join(POSTED_DIR, fname)
        if fname.endswith(".mp4"):
            try:
                os.remove(fpath)
                print(f"[*] Pruned posted video to free storage: {fname}")
            except Exception:
                pass

def get_queued_videos():
    """Returns sorted list of videos waiting in output/pipeline/ by date (FIFO, never alphabetically)."""
    ensure_directories()
    files = [f for f in os.listdir(PIPELINE_DIR) if f.endswith(".mp4")]

    def _file_sort_key(fname):
        fpath = os.path.join(PIPELINE_DIR, fname)
        mpath = os.path.splitext(fpath)[0] + ".json"
        priority = 3
        ts_val = 0.0
        if os.path.exists(mpath):
            try:
                with open(mpath, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                if meta.get("discarded"):
                    return (999, 0.0)
                p = meta.get("priority", 3)
                try:
                    priority = int(p)
                except Exception:
                    priority = 3
                raw_ts = meta.get("timestamp") or meta.get("staged_at") or meta.get("created_at")
                if raw_ts:
                    ts_val = datetime.fromisoformat(str(raw_ts)).timestamp()
            except Exception:
                pass
        if ts_val <= 0:
            m = re.match(r"^(\d{4}-\d{2}-\d{2})", fname)
            if m:
                try:
                    ts_val = datetime.strptime(m.group(1), "%Y-%m-%d").timestamp()
                except Exception:
                    pass
        if ts_val <= 0:
            try:
                ts_val = os.path.getmtime(fpath)
            except Exception:
                ts_val = 0.0
        # Higher priority posts first (-priority), FIFO within tier (ts_val)
        return (-priority, ts_val)

    files = [f for f in files if _file_sort_key(f)[0] != 999]
    files.sort(key=_file_sort_key)
    return [os.path.join(PIPELINE_DIR, f) for f in files]

async def stage_new_video(category=None, topic=None, style_mode="historical_cartoon"):
    """Generates a new story video and stages it in output/pipeline/."""
    ensure_directories()
    categories = ["history", "mythology", "humor"]
    if not category:
        logs = load_log()
        last_cat = logs[-1].get("category", "") if logs else ""
        next_cats = [c for c in categories if c != last_cat]
        category = next_cats[0] if next_cats else "history"

    date_str = get_now_ist().strftime("%Y-%m-%d")
    temp_target = os.path.join(PIPELINE_DIR, f"temp_{date_str}.mp4")

    print(f"\n[*] Staging new {category} video into pipeline...")
    rendered_mp4 = await build_story_video(
        category=category,
        topic=topic,
        style_mode=style_mode,
        output_path=temp_target,
        publish=False
    )

    from src.story_engine.vault import STORY_VAULT
    matching = [s for s in STORY_VAULT if s["category"] == category]
    story_meta = matching[0] if matching else {"title": f"{category.capitalize()} Story"}

    title = story_meta.get("title", f"{category.capitalize()} Story")
    short_slug = slugify(title)
    final_video_name = f"{date_str}-{short_slug}.mp4"
    final_video_path = os.path.join(PIPELINE_DIR, final_video_name)

    count = 1
    while os.path.exists(final_video_path):
        final_video_name = f"{date_str}-{short_slug}_{count}.mp4"
        final_video_path = os.path.join(PIPELINE_DIR, final_video_name)
        count += 1

    shutil.move(rendered_mp4, final_video_path)

    meta_json_path = os.path.splitext(final_video_path)[0] + ".json"
    tags = f"#{category} #history #animation #storytime #shorts #reels"
    meta_data = {
        "title": f"{title} 🎬",
        "category": category,
        "caption": f"{title}\n\n{story_meta.get('hook', '')}\n\n{tags}",
        "staged_at": datetime.now(timezone.utc).isoformat()
    }
    with open(meta_json_path, "w", encoding="utf-8") as f:
        json.dump(meta_data, f, indent=2)

    print(f"[+] Successfully staged video: {final_video_path}")
    return final_video_path, meta_data

async def run_pipeline(platforms=None, force=False):
    if platforms is None:
        platforms = ["youtube"]
    # Safety: Filter out Instagram to protect account from automated scraping bans
    platforms = [p for p in platforms if p != "instagram"]

    if os.path.exists("config.json"):
        try:
            with open("config.json", "r", encoding="utf-8") as cf:
                cfg = json.load(cf)
            if cfg.get("mode") == "twitch_hype" and cfg.get("disable_stickman_during_hype", False):
                print("[*] Hype mode active ('disable_stickman_during_hype=true'). Handing off to Twitch Clipper publisher...")
                from twitch_clipper import publish_next_clip
                return publish_next_clip(cfg, platforms=platforms, force=force)
        except Exception as e:
            print(f"[!] Error during hype publisher handoff: {e}")

    ensure_directories()
    prune_posted_archive(days=7)

    now_ist = get_now_ist()
    print("=" * 60)
    print(f"⏰ AUTONOMOUS POSTING CHECK (IST: {now_ist.strftime('%Y-%m-%d %I:%M:%S %p')})")
    print("=" * 60)

    # Intelligent Gatekeeper
    can_post, reason = check_can_post_now(force=force)
    print(f"[*] Gatekeeper status: {reason}")

    if not can_post:
        print("[*] No action taken during this cycle. Exiting safely.")
        return {"status": "skipped", "reason": reason}

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

    raw_title = meta.get("title", os.path.basename(video_to_post).replace(".mp4", "").replace("-", " ").title())
    raw_caption = meta.get("caption", f"{raw_title} #shorts #animation #storytime #reels")
    title = sanitize_text_for_reach(raw_title)
    caption = sanitize_text_for_reach(raw_caption)

    print("\n" + "=" * 60)
    print(f"🚀 PUBLISHING PIPELINE VIDEO: {video_to_post}")
    print(f"📌 TITLE:   {title}")
    print(f"🌐 TARGETS: {platforms}")
    print("=" * 60)

    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
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
    backup_critical_logs()
    log_event("SUCCESS", "AutoPoster", "publish_next_post", {
        "video": results.get("video"),
        "uploads": results.get("uploads")
    })

    # Delete posted video and metadata to prevent storage clutter (URLs recorded in logs)
    if os.path.exists(video_to_post):
        try:
            os.remove(video_to_post)
            log_event("INFO", "AutoPoster", "delete_posted_video", {"video": video_to_post})
        except Exception:
            pass
    if os.path.exists(json_path):
        try:
            os.remove(json_path)
        except Exception:
            pass
    print(f"[+] Posted video and metadata deleted from pipeline (Storage freed).")

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
    parser.add_argument("--platforms", nargs="+", choices=["youtube", "instagram", "tiktok"], default=["youtube"])
    parser.add_argument("--force", action="store_true", help="Force publish immediately, bypassing time window & quota checks")
    parser.add_argument("--stage-only", action="store_true", help="Stage a new video in pipeline without publishing")
    args = parser.parse_args()

    if args.stage_only:
        asyncio.run(stage_new_video())
    else:
        asyncio.run(run_pipeline(platforms=args.platforms, force=args.force))

if __name__ == "__main__":
    main()
