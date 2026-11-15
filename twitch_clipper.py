"""
HyperClip AI - Autonomous Twitch Hype Clipper & Multi-Platform Publisher.
Monitors live & recent VODs of target streamers, detects chat velocity spikes,
extracts 35s highlight clips via TwitchDownloaderCLI, reframes to 9:16 portrait
(stacked facecam top + gameplay bottom on solid black), generates Whisper captions,
and publishes to YouTube Shorts + Secondary Instagram Account.
"""

import os
import re
import json
import shutil
import argparse
from datetime import datetime, timezone, timedelta

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from src.twitch_clipper.twitch_gql import find_clippable_targets
from src.twitch_clipper.downloader import download_chat, download_video_segment
from src.twitch_clipper.hype_detector import detect_hype_moments
from src.twitch_clipper.captioner import generate_clip_captions
from src.twitch_clipper.video_framer import frame_to_portrait
from src.uploaders.youtube_uploader import upload_short
from src.uploaders.instagram_uploader import upload_reel_direct

CONFIG_FILE = "config.json"
STATE_FILE = "clipper_state.json"
TWITCH_LOG_FILE = "posted_twitch_log.json"
TWITCH_PIPELINE_DIR = os.path.join("output", "twitch_pipeline")
TWITCH_POSTED_DIR = os.path.join("output", "twitch_posted")
TEMP_DIR = "temp_twitch"

IST = timezone(timedelta(hours=5, minutes=30))


def load_config() -> dict:
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_json(path: str, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default


def _save_json(path: str, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def ensure_dirs():
    os.makedirs(TWITCH_PIPELINE_DIR, exist_ok=True)
    os.makedirs(TWITCH_POSTED_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:28]


def prune_twitch_archive(days: int = 7):
    ensure_dirs()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    for fname in os.listdir(TWITCH_POSTED_DIR):
        if not fname.endswith((".mp4", ".json")):
            continue
        fpath = os.path.join(TWITCH_POSTED_DIR, fname)
        mtime = datetime.fromtimestamp(os.path.getmtime(fpath), tz=timezone.utc)
        if mtime < cutoff:
            os.remove(fpath)
            print(f"[*] Pruned expired Twitch clip (>7 days): {fname}")


def harvest_clips(config: dict, max_total_new: int = 4) -> list:
    """
    Scans eligible streamers, downloads unscanned chat windows, detects hype spikes,
    and stages framed + captioned portrait clips into output/twitch_pipeline/.
    """
    ensure_dirs()
    tc = config.get("twitch_clipper", {})
    state = _load_json(STATE_FILE, {"vods": {}})

    targets = find_clippable_targets(config)
    if not targets:
        print("[*] No streamers currently meet live/VOD eligibility criteria.")
        return []

    print(f"[*] Found {len(targets)} eligible stream/VOD targets.")
    staged_clips = []

    for target in targets:
        if len(staged_clips) >= max_total_new:
            break

        vod_id = str(target["vod_id"])
        vod_state = state["vods"].get(vod_id, {"last_scanned_sec": 0, "clipped_peaks": []})
        last_sec = int(vod_state.get("last_scanned_sec", 0))
        dur_sec = int(target.get("duration_sec", 0))

        # Skip if less than 15 minutes of new footage since last scan
        if not target["is_live"] and last_sec > 0 and (dur_sec - last_sec) < 300:
            continue
        if target["is_live"] and last_sec > 0 and (dur_sec - last_sec) < 900:
            continue

        chat_json = os.path.join(TEMP_DIR, f"chat_{vod_id}.json")
        try:
            # For live VODs, scan from last_sec up to current dur_sec (or full if first scan)
            scan_start = max(0, last_sec - 30) if last_sec > 0 else 0
            download_chat(vod_id, chat_json, start_sec=scan_start if scan_start > 0 else None)
        except Exception as e:
            print(f"[-] Chat download failed for {target['username']} ({vod_id}): {e}")
            continue

        moments = detect_hype_moments(
            chat_json,
            pre_peak_sec=tc.get("pre_peak_sec", 22),
            post_peak_sec=tc.get("post_peak_sec", 13),
            max_clips=tc.get("max_clips_per_vod", 4),
            min_spacing_sec=tc.get("min_clip_spacing_sec", 180),
            min_spike_sigma=tc.get("min_spike_sigma", 2.0),
            min_messages_per_window=tc.get("min_messages_per_window", 12),
        )

        # Update last scanned offset
        vod_state["last_scanned_sec"] = max(last_sec, dur_sec)

        if not moments:
            print(f"[-] No hype spikes detected in {target['display_name']} VOD {vod_id}.")
            state["vods"][vod_id] = vod_state
            _save_json(STATE_FILE, state)
            continue

        already_clipped = vod_state.get("clipped_peaks", [])
        min_spacing = tc.get("min_clip_spacing_sec", 180)

        for m in moments:
            if len(staged_clips) >= max_total_new:
                break
            peak = m["peak_sec"]
            if any(abs(peak - old) < min_spacing for old in already_clipped):
                continue

            raw_clip = os.path.join(TEMP_DIR, f"raw_{vod_id}_{peak}.mp4")
            ass_path = os.path.join(TEMP_DIR, f"subs_{vod_id}_{peak}.ass")
            date_str = datetime.now(IST).strftime("%Y-%m-%d")
            slug = slugify(f"{target['username']}_{vod_id}_{peak}")
            out_mp4 = os.path.join(TWITCH_PIPELINE_DIR, f"{date_str}-{slug}.mp4")
            out_json = os.path.join(TWITCH_PIPELINE_DIR, f"{date_str}-{slug}.json")

            try:
                download_video_segment(vod_id, m["start_sec"], m["end_sec"], raw_clip)

                sub_file = None
                if tc.get("enable_captions", True):
                    sub_file = generate_clip_captions(
                        raw_clip, ass_path, model_size=tc.get("whisper_model", "tiny.en")
                    )

                frame_to_portrait(
                    raw_clip,
                    out_mp4,
                    ass_subtitle_path=sub_file,
                    layout=tc.get("layout", "auto_stacked"),
                )

                game_tag = slugify(target.get("game", "gaming")).replace("_", "")
                hashtags = tc.get("default_hashtags", "#twitch #gaming #shorts #reels")
                clip_title = f"{target['display_name']} Insane {target.get('game', 'Stream')} Moment!"
                clip_caption = (
                    f"{target['display_name']} goes crazy on {target.get('game', 'stream')}! "
                    f"#{target['username']} #{game_tag} {hashtags}"
                )

                meta = {
                    "streamer": target["display_name"],
                    "username": target["username"],
                    "vod_id": vod_id,
                    "game": target.get("game", "Unknown"),
                    "peak_sec": peak,
                    "hype_score": m["score"],
                    "z_score": m["z_score"],
                    "title": clip_title,
                    "caption": clip_caption,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                _save_json(out_json, meta)
                already_clipped.append(peak)
                staged_clips.append(out_mp4)
                print(f"[+] Staged Twitch clip: {out_mp4} (z={m['z_score']}, msgs={m['msg_count_15s']})")
            except Exception as e:
                print(f"[-] Failed processing clip {vod_id}@{peak}s: {e}")
            finally:
                for tmp in (raw_clip, ass_path):
                    if os.path.exists(tmp):
                        try:
                            os.remove(tmp)
                        except Exception:
                            pass

        vod_state["clipped_peaks"] = already_clipped
        state["vods"][vod_id] = vod_state
        _save_json(STATE_FILE, state)

        if os.path.exists(chat_json):
            try:
                os.remove(chat_json)
            except Exception:
                pass

    return staged_clips


def check_can_publish_twitch(config: dict, force: bool = False) -> tuple:
    if force:
        return True, "Force mode active"

    tc = config.get("twitch_clipper", {})
    max_daily = tc.get("max_daily_posts", 4)
    min_gap = tc.get("min_gap_hours", 2.5)

    now_ist = datetime.now(IST)
    today_str = now_ist.strftime("%Y-%m-%d")
    logs = _load_json(TWITCH_LOG_FILE, [])

    today_posts = []
    last_post = None
    for entry in logs:
        uploads = entry.get("uploads", {})
        if not any(isinstance(v, str) and not v.lower().startswith("failed") for v in uploads.values()):
            continue
        ts_str = entry.get("timestamp")
        if not ts_str:
            continue
        try:
            dt_ist = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).astimezone(IST)
            if dt_ist.strftime("%Y-%m-%d") == today_str:
                today_posts.append(dt_ist)
            if last_post is None or dt_ist > last_post:
                last_post = dt_ist
        except Exception:
            pass

    if len(today_posts) >= max_daily:
        return False, f"Twitch daily limit reached ({len(today_posts)}/{max_daily} today)"

    if last_post:
        elapsed = (now_ist - last_post).total_seconds() / 3600.0
        if elapsed < min_gap:
            return False, f"Cooldown active ({elapsed:.1f}h < {min_gap}h)"

    return True, f"Eligible ({len(today_posts) + 1}/{max_daily} today)"


def publish_next_clip(config: dict, platforms: list = None, force: bool = False) -> dict:
    if platforms is None:
        platforms = ["youtube", "instagram"]

    ensure_dirs()
    prune_twitch_archive(days=7)

    queued = sorted([f for f in os.listdir(TWITCH_PIPELINE_DIR) if f.endswith(".mp4")])
    if not queued:
        print("[*] Twitch pipeline empty. Harvesting new hype clips first...")
        harvest_clips(config, max_total_new=3)
        queued = sorted([f for f in os.listdir(TWITCH_PIPELINE_DIR) if f.endswith(".mp4")])

    if not queued:
        return {"status": "empty", "reason": "No clips found in pipeline or live streams."}

    can_post, reason = check_can_publish_twitch(config, force=force)
    print(f"[*] Twitch Gatekeeper: {reason}")
    if not can_post:
        return {"status": "skipped", "reason": reason}

    tc = config.get("twitch_clipper", {})
    ig_slot = tc.get("instagram_account_slot", 2)

    clip_name = queued[0]
    clip_path = os.path.join(TWITCH_PIPELINE_DIR, clip_name)
    meta_path = os.path.splitext(clip_path)[0] + ".json"
    meta = _load_json(meta_path, {})

    title = meta.get("title", clip_name.replace(".mp4", "").replace("_", " ").title())
    caption = meta.get("caption", f"{title} #shorts #twitch #gaming")

    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "video": clip_name,
        "streamer": meta.get("username", "unknown"),
        "title": title,
        "uploads": {},
    }

    if "youtube" in platforms:
        try:
            yt_url = upload_short(clip_path, title=title, description=caption)
            results["uploads"]["youtube"] = yt_url
        except Exception as e:
            print(f"[-] YouTube upload error: {e}")
            results["uploads"]["youtube"] = f"Failed: {e}"

    if "instagram" in platforms:
        suffix = "" if ig_slot == 1 else f"_{ig_slot}"
        if os.getenv(f"INSTA_USERNAME{suffix}") and os.getenv(f"INSTA_PASSWORD{suffix}"):
            try:
                code = upload_reel_direct(clip_path, caption, account_slot=ig_slot)
                results["uploads"]["instagram"] = f"https://instagram.com/reel/{code}"
            except Exception as e:
                print(f"[-] Instagram (slot {ig_slot}) upload error: {e}")
                results["uploads"]["instagram"] = f"Failed: {e}"
        else:
            print(f"[!] INSTA_USERNAME{suffix} / INSTA_PASSWORD{suffix} not set. Skipping Instagram slot {ig_slot}.")

    if any(isinstance(v, str) and not v.lower().startswith("failed") for v in results["uploads"].values()):
        logs = _load_json(TWITCH_LOG_FILE, [])
        logs.append(results)
        _save_json(TWITCH_LOG_FILE, logs)

        shutil.move(clip_path, os.path.join(TWITCH_POSTED_DIR, clip_name))
        if os.path.exists(meta_path):
            shutil.move(meta_path, os.path.join(TWITCH_POSTED_DIR, os.path.basename(meta_path)))
        print(f"[+] Archived posted Twitch clip to {TWITCH_POSTED_DIR}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HyperClip AI - Twitch Hype Clipper")
    parser.add_argument("--harvest-only", action="store_true", help="Only scan and stage clips without posting")
    parser.add_argument("--check-only", action="store_true", help="Check live/VOD targets and exit")
    parser.add_argument("--force", action="store_true", help="Bypass daily cap and cooldown")
    parser.add_argument("--platforms", nargs="+", default=["youtube", "instagram"])
    args = parser.parse_args()

    cfg = load_config()
    if args.check_only:
        t = find_clippable_targets(cfg)
        print(json.dumps(t, indent=2))
    elif args.harvest_only:
        harvest_clips(cfg)
    else:
        publish_next_clip(cfg, platforms=args.platforms, force=args.force)
