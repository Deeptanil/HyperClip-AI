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
from src.twitch_clipper.video_framer import frame_to_portrait, detect_facecam_region, get_video_dimensions
from src.twitch_clipper.hook_generator import generate_hook_text, render_hook_banner, slugify_hook
from src.twitch_clipper.content_judge import evaluate_clip_quality
from src.twitch_clipper.nsfw_censor import scan_and_censor_nsfw
from src.uploaders.youtube_uploader import upload_short
from src.uploaders.instagram_uploader import upload_reel, upload_reel_direct

CONFIG_FILE = "config.json"
STATE_FILE = "clipper_state.json"
TWITCH_LOG_FILE = "posted_twitch_log.json"
STREAM_PIPELINE_DIR = os.path.join("output", "stream_pipeline")
STREAM_POSTED_DIR = os.path.join("output", "stream_posted")
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
    os.makedirs(STREAM_PIPELINE_DIR, exist_ok=True)
    os.makedirs(STREAM_POSTED_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)


def _extract_transcript_from_ass(ass_path: str) -> str:
    """Extracts spoken words from generated ASS karaoke file for AI hook context."""
    if not ass_path or not os.path.exists(ass_path):
        return ""
    words = []
    seen = set()
    try:
        with open(ass_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("Dialogue:"):
                    parts = line.split(",,", 1)
                    if len(parts) < 2:
                        continue
                    # Extract the highlighted word inside {\c&H0000FFFF&}WORD{\c&H00FFFFFF&}
                    m = re.search(r"\\c&H0000FFFF&\}([^\{]+)\{", parts[1])
                    if m:
                        w = m.group(1).strip()
                        if w:
                            words.append(w)
    except Exception:
        pass
    return " ".join(words)[:300]


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:28]


def _get_directory_size_mb(path: str) -> float:
    """Calculates total size of directory in megabytes."""
    total_bytes = 0
    if os.path.exists(path):
        for root, _, files in os.walk(path):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    total_bytes += os.path.getsize(fp)
                except OSError:
                    pass
    return total_bytes / (1024.0 * 1024.0)


def enforce_storage_limits(config: dict):
    """
    Monitors repository media storage against 80% and 90% watermarks:
    - At 80%: Cleans temporary files, cache, and posted archives older than 5 days.
    - At 90%: Aggressively purges oldest posted archives until storage is <= 80%.
    - SAFEGUARD: NEVER deletes unposted clips in stream_pipeline/.
    """
    ensure_dirs()
    sg = config.get("storage_governor", {})
    if not sg.get("enabled", True):
        return

    max_mb = float(sg.get("max_repo_mb", 1500))
    cleanup_pct = float(sg.get("cleanup_threshold_percent", 80))
    aggressive_pct = float(sg.get("aggressive_threshold_percent", 90))

    posted_mb = _get_directory_size_mb(STREAM_POSTED_DIR)
    pipeline_mb = _get_directory_size_mb(STREAM_PIPELINE_DIR)
    temp_mb = _get_directory_size_mb(TEMP_DIR)
    total_media_mb = posted_mb + pipeline_mb + temp_mb

    usage_pct = (total_media_mb / max_mb) * 100.0
    print(f"[*] Storage check: {total_media_mb:.1f}MB / {max_mb:.1f}MB ({usage_pct:.1f}% used) [Pipeline: {pipeline_mb:.1f}MB, Posted: {posted_mb:.1f}MB]")

    # 1. Clean temp_twitch if not empty
    if os.path.exists(TEMP_DIR) and os.listdir(TEMP_DIR):
        for f in os.listdir(TEMP_DIR):
            fp = os.path.join(TEMP_DIR, f)
            try:
                if os.path.isfile(fp):
                    os.remove(fp)
            except OSError:
                pass

    # 2. Level 1 Cleanup (>= 80%): Prune posted archive older than 5 days
    if usage_pct >= cleanup_pct:
        print(f"[!] Storage watermark reached ({usage_pct:.1f}% >= {cleanup_pct}%). Running standard posted prune...")
        prune_stream_archive(days=sg.get("max_posted_archive_days", 5))
        posted_mb = _get_directory_size_mb(STREAM_POSTED_DIR)
        total_media_mb = posted_mb + pipeline_mb
        usage_pct = (total_media_mb / max_mb) * 100.0

    # 3. Level 2 Aggressive Purge (>= 90%): Delete oldest posted files until <= 80%
    if usage_pct >= aggressive_pct:
        print(f"[!] CRITICAL: Storage exceeds aggressive limit ({usage_pct:.1f}% >= {aggressive_pct}%). Purging posted archive...")
        posted_files = []
        for fname in os.listdir(STREAM_POSTED_DIR):
            if fname.endswith((".mp4", ".json")):
                fp = os.path.join(STREAM_POSTED_DIR, fname)
                try:
                    posted_files.append((fp, os.path.getmtime(fp)))
                except OSError:
                    pass
        # Sort oldest first
        posted_files.sort(key=lambda x: x[1])
        for fp, _ in posted_files:
            try:
                os.remove(fp)
                print(f"[*] Aggressive purge deleted: {os.path.basename(fp)}")
            except OSError:
                pass
            posted_mb = _get_directory_size_mb(STREAM_POSTED_DIR)
            total_media_mb = posted_mb + pipeline_mb
            if (total_media_mb / max_mb) * 100.0 <= cleanup_pct:
                break

    # 4. Pipeline Warning Safeguard (Unposted clips are NEVER deleted)
    if (pipeline_mb / max_mb) * 100.0 >= cleanup_pct:
        print(f"[!] WARNING: Unposted pipeline queue alone is taking {pipeline_mb:.1f}MB ({pipeline_mb/max_mb*100:.1f}% of limit).")
        print("[!] SAFEGUARD: Pending posts will NOT be deleted. Existing queue should be published before staging more clips.")


def prune_stream_archive(days: int = 7):
    ensure_dirs()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    for fname in os.listdir(STREAM_POSTED_DIR):
        if not fname.endswith((".mp4", ".json")):
            continue
        fpath = os.path.join(STREAM_POSTED_DIR, fname)
        mtime = datetime.fromtimestamp(os.path.getmtime(fpath), tz=timezone.utc)
        if mtime < cutoff:
            os.remove(fpath)
            print(f"[*] Pruned expired clip (>7 days): {fname}")


def harvest_clips(config: dict, max_total_new: int = 4) -> list:
    """
    Scans eligible streamers, downloads unscanned chat windows, detects hype spikes,
    and stages framed + captioned portrait clips into output/stream_pipeline/.
    """
    ensure_dirs()
    enforce_storage_limits(config)
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
            # For live VODs, scan from last_sec or most recent 25 mins of live action
            if target.get("is_live"):
                scan_start = max(0, last_sec - 30) if last_sec > 0 else max(0, dur_sec - 1500)
            else:
                scan_start = max(0, last_sec - 30) if last_sec > 0 else 0
            download_chat(vod_id, chat_json, start_sec=scan_start if scan_start > 0 else None)
        except Exception as e:
            print(f"[-] Chat download failed for {target['username']} ({vod_id}): {e}")
            continue

        moments = detect_hype_moments(
            chat_json,
            pre_peak_sec=tc.get("pre_peak_sec", 22),
            post_peak_sec=tc.get("post_peak_sec", 13),
            max_clips=tc.get("max_clips_per_vod", 3),
            min_spacing_sec=tc.get("min_clip_spacing_sec", 300),
            min_spike_sigma=tc.get("min_spike_sigma", 2.0),
            min_messages_per_window=tc.get("min_messages_per_window", 12),
            viewers=target.get("viewers", 0),
            intro_skip_sec=tc.get("intro_skip_sec", 480),
        )

        # Update last scanned offset
        vod_state["last_scanned_sec"] = max(last_sec, dur_sec)

        if not moments:
            print(f"[-] No hype spikes detected in {target['display_name']} VOD {vod_id}.")
            state["vods"][vod_id] = vod_state
            _save_json(STATE_FILE, state)
            continue

        already_clipped = vod_state.get("clipped_peaks", [])
        min_spacing = tc.get("min_clip_spacing_sec", 300)

        for m in moments:
            if len(staged_clips) >= max_total_new:
                break
            peak = m["peak_sec"]
            if any(abs(peak - old) < min_spacing for old in already_clipped):
                continue

            raw_clip = os.path.join(TEMP_DIR, f"raw_{vod_id}_{peak}.mp4")
            ass_path = os.path.join(TEMP_DIR, f"subs_{vod_id}_{peak}.ass")
            banner_path = os.path.join(TEMP_DIR, f"banner_{vod_id}_{peak}.png")
            date_str = datetime.now(IST).strftime("%Y-%m-%d")

            try:
                download_video_segment(vod_id, m["start_sec"], m["end_sec"], raw_clip)

                # Check facecam layout & presence
                raw_w, raw_h, _ = get_video_dimensions(raw_clip)
                facecam_box = detect_facecam_region(
                    raw_clip, raw_w, raw_h, streamer=target["username"], game=target.get("game", "")
                )

                sub_file = None
                if tc.get("enable_captions", True):
                    sub_file = generate_clip_captions(
                        raw_clip, ass_path, model_size=tc.get("whisper_model", "tiny.en")
                    )

                transcript_text = _extract_transcript_from_ass(sub_file)

                # AI Content Quality & Viral Judge: Vets visual motion, streamer presence & entertainment value
                eval_res = evaluate_clip_quality(
                    streamer=target["display_name"],
                    game=target.get("game", "Stream"),
                    stream_title=target.get("title", ""),
                    sample_chat=m.get("sample_chat", []),
                    transcript=transcript_text or None,
                    raw_clip_path=raw_clip,
                    facecam=facecam_box,
                )

                if not eval_res["approved"]:
                    print(f"[-] Clip rejected by Content Judge: {eval_res['reason']}")
                    already_clipped.append(peak)
                    continue

                # Automated Sexual / NSFW Content Detection & Censoring
                safety_cfg = config.get("content_safety", {})
                nsfw_res = {"action": "clean", "segments": []}
                if safety_cfg.get("auto_censor_nsfw", True):
                    nsfw_res = scan_and_censor_nsfw(
                        raw_clip,
                        censor_mode=safety_cfg.get("censor_mode", "blur"),
                        max_nsfw_ratio=float(safety_cfg.get("max_nsfw_ratio_before_reject", 0.65)),
                    )
                    if nsfw_res["action"] == "rejected":
                        print(f"[-] Clip rejected by NSFW Safety Shield: {nsfw_res['reason']}")
                        already_clipped.append(peak)
                        continue

                hook_headline = eval_res.get("hook")
                if not hook_headline:
                    hook_headline = generate_hook_text(
                        streamer=target["display_name"],
                        game=target.get("game", "Stream"),
                        stream_title=target.get("title", ""),
                        sample_chat=m.get("sample_chat", []),
                        transcript=transcript_text or None,
                    )
                render_hook_banner(hook_headline, banner_path)

                hook_slug = slugify_hook(hook_headline)
                base_name = f"{date_str}-{hook_slug}"
                out_mp4 = os.path.join(STREAM_PIPELINE_DIR, f"{base_name}.mp4")
                if os.path.exists(out_mp4) or os.path.exists(os.path.join(STREAM_POSTED_DIR, f"{base_name}.mp4")):
                    base_name = f"{date_str}-{hook_slug}_{peak}"
                    out_mp4 = os.path.join(STREAM_PIPELINE_DIR, f"{base_name}.mp4")
                out_json = os.path.join(STREAM_PIPELINE_DIR, f"{base_name}.json")

                frame_to_portrait(
                    raw_clip,
                    out_mp4,
                    ass_subtitle_path=sub_file,
                    banner_png=banner_path,
                    layout=tc.get("layout", "auto_stacked"),
                    streamer=target["username"],
                    game=target.get("game", ""),
                )

                game_tag = slugify(target.get("game", "gaming")).replace("_", "")
                hashtags = tc.get("default_hashtags", "#twitch #gaming #shorts #reels")
                clip_title = hook_headline
                clip_caption = eval_res.get("caption")
                if not clip_caption:
                    clip_caption = (
                        f"{hook_headline}\n\n"
                        f"{target['display_name']} on {target.get('game', 'stream')}! "
                        f"#{target['username']} #{game_tag} {hashtags}"
                    )

                # Account Assignment & YouTube Ratio:
                sched = config.get("publishing_schedule", {})
                ig_accounts = sched.get("instagram_accounts", [])
                ig_any_enabled = any(a.get("enabled", False) for a in ig_accounts)

                if not ig_any_enabled:
                    # Instagram automations PAUSED to protect account integrity. Route 100% of clips to YouTube Shorts!
                    schedule_for_yt = True
                    target_accounts = ["youtube"]
                    target_label = "YouTube Shorts"
                    assigned_ig = None
                else:
                    # 2 Instagrams (@solvikz and @loopablez) vs 1 YouTube channel.
                    # 1. Instagram: Alternate between ig_1 and ig_2 based on current queue count.
                    ig1_queued = 0
                    ig2_queued = 0
                    for f in os.listdir(STREAM_PIPELINE_DIR):
                        if f.endswith(".json"):
                            cm = _load_json(os.path.join(STREAM_PIPELINE_DIR, f), {})
                            accs = cm.get("target_accounts", [])
                            if "ig_1" in accs or cm.get("assigned_ig") == "ig_1":
                                ig1_queued += 1
                            if "ig_2" in accs or cm.get("assigned_ig") == "ig_2":
                                ig2_queued += 1

                    assigned_ig = "ig_1" if ig1_queued <= ig2_queued else "ig_2"
                    ig_name = "Solvikz" if assigned_ig == "ig_1" else "Loopablez"

                    # 2. YouTube: Exactly 50% of clips generated will be posted on YouTube.
                    yt_toggle = state.get("yt_toggle", True)
                    schedule_for_yt = yt_toggle
                    state["yt_toggle"] = not yt_toggle

                    target_accounts = [assigned_ig]
                    if schedule_for_yt:
                        target_accounts.append("youtube")
                        target_label = f"Instagram (@{ig_name.lower()}) & YouTube"
                    else:
                        target_label = f"Instagram (@{ig_name.lower()}) Only"

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
                    "hook": hook_headline,
                    "target_accounts": target_accounts,
                    "assigned_ig": assigned_ig,
                    "post_to_yt": schedule_for_yt,
                    "post_to_ig": True,
                    "posted_to_instagram": False,
                    "posted_to_youtube": False,
                    "approval_status": "pending",
                    "priority": "auto",
                    "nsfw_censored": nsfw_res.get("action") == "censored",
                    "nsfw_segments": nsfw_res.get("segments", []),
                    "target": target_label,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                _save_json(out_json, meta)
                already_clipped.append(peak)
                staged_clips.append(out_mp4)
                print(f"[+] Staged Twitch clip: {out_mp4} (hook='{hook_headline}', target='{target_label}', z={m['z_score']})")
            except Exception as e:
                print(f"[-] Failed processing clip {vod_id}@{peak}s: {e}")
            finally:
                for tmp in (raw_clip, ass_path, banner_path):
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


def _get_today_stats(logs: list) -> dict:
    """Computes today's (IST) upload counts and last timestamps per destination."""
    now_ist = datetime.now(IST)
    today_str = now_ist.strftime("%Y-%m-%d")

    stats = {
        "youtube": {"count": 0, "last": None},
        "ig_1": {"regular": 0, "trial": 0, "last": None},
        "ig_2": {"regular": 0, "trial": 0, "last": None},
    }

    for entry in logs:
        ts_str = entry.get("timestamp")
        if not ts_str:
            continue
        try:
            dt_ist = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).astimezone(IST)
        except Exception:
            continue

        uploads = entry.get("uploads", {})
        is_today = dt_ist.strftime("%Y-%m-%d") == today_str

        yt_val = uploads.get("youtube")
        if isinstance(yt_val, str) and not yt_val.lower().startswith("failed"):
            if is_today:
                stats["youtube"]["count"] += 1
            if stats["youtube"]["last"] is None or dt_ist > stats["youtube"]["last"]:
                stats["youtube"]["last"] = dt_ist

        for slot in (1, 2):
            key = f"ig_{slot}"
            for kind in ("regular", "trial"):
                u_key = f"instagram_{slot}_{kind}"
                val = uploads.get(u_key)
                if isinstance(val, str) and not val.lower().startswith("failed"):
                    if is_today:
                        stats[key][kind] += 1
                    if stats[key]["last"] is None or dt_ist > stats[key]["last"]:
                        stats[key]["last"] = dt_ist

    return stats


def get_account_interval_minutes(posts_per_day: int) -> float:
    """
    Computes required gap between posts for an account:
    Interval = (24 * 60 / posts_per_day) - 30 minutes buffer.
    Minimum safe gap: 15 minutes.
    """
    if posts_per_day is None or posts_per_day <= 0:
        return float("inf")
    gap = (24.0 * 60.0 / float(posts_per_day)) - 30.0
    return max(15.0, gap)


def compute_clip_priority(meta: dict, config: dict, filename: str = "") -> tuple[int, str]:
    """
    4-Tier Posting Priority Order (lower rank posts first):
      0 = prioritized   : Manually prioritized OR matches prioritized_categories (e.g. GTA 6)
      1 = approved      : Manually approved
      2 = normal        : Default / no category
      3 = deprioritized : Manually deprioritized OR matches deprioritized_categories (posts ONLY when no higher priority exists)
      9 = denied        : Excluded from publishing
    """
    status = str(meta.get("approval_status", meta.get("status", "pending"))).lower().strip()
    if status == "denied":
        return 9, "denied"

    explicit = str(meta.get("priority", "")).lower().strip()
    if explicit == "prioritized":
        return 0, "prioritized"
    if explicit == "approved":
        return 1, "approved"
    if explicit == "normal":
        return 2, "normal"
    if explicit in ("deprioritized", "unprioritized"):
        return 3, "deprioritized"

    # Category / Game rules from config.json
    rules = config.get("publishing_schedule", {}).get("priority_rules", {})
    prio_cats = [str(c).lower().strip() for c in rules.get("prioritized_categories", []) if str(c).strip()]
    deprio_cats = [str(c).lower().strip() for c in rules.get("deprioritized_categories", []) if str(c).strip()]

    haystack = " ".join([
        str(meta.get("game", "")),
        str(meta.get("category", "")),
        str(meta.get("title", "")),
        str(meta.get("caption", "")),
        str(meta.get("hook", "")),
        str(filename),
    ]).lower()

    if any(cat in haystack for cat in prio_cats):
        return 0, "prioritized"
    if status == "approved":
        return 1, "approved"
    if any(cat in haystack for cat in deprio_cats):
        return 3, "deprioritized"
    return 2, "normal"


def _pick_next_ig_action(acc_cfg: dict, acc_stats: dict, last_any_ig: datetime | None, cross_gap_min: int = 25, force: bool = False) -> str | None:
    """
    Returns 'regular', 'trial', or None for an Instagram account slot.
    Enforces dynamic gap calculation based on posts/day (0 = paused) and strict cross-account separation.
    """
    if not acc_cfg.get("enabled", True):
        return None

    now_ist = datetime.now(IST)
    reg_count = acc_stats.get("regular", 0)
    trial_count = acc_stats.get("trial", 0)
    total_today = reg_count + trial_count
    reg_target = int(acc_cfg.get("regular_per_day", 0) or 0)
    trial_target = int(acc_cfg.get("trial_per_day", 0) or 0)
    posts_per_day = reg_target + trial_target
    if posts_per_day <= 0:
        print(f"[-] {acc_cfg.get('name', 'IG')} is set to 0 posts/day (Paused).")
        return None

    hard_ceiling = int(acc_cfg.get("hard_daily_ceiling", posts_per_day) if acc_cfg.get("hard_daily_ceiling") is not None else posts_per_day)
    effective_cap = min(posts_per_day, hard_ceiling)
    if effective_cap <= 0:
        return None

    # 1. HARD CEILING: Never exceed daily quota in 24 hours
    if total_today >= effective_cap:
        print(f"[-] Daily cap reached for {acc_cfg.get('name', 'IG')} ({total_today}/{effective_cap} today). Refusing to post.")
        return None

    # 2. DYNAMIC SPACING: (24h / posts_per_day) - 30m buffer (bypassed if force=True)
    if not force:
        last_self = acc_stats.get("last")
        gap_minutes = get_account_interval_minutes(posts_per_day)
        if last_self:
            elapsed_self_m = (now_ist - last_self).total_seconds() / 60.0
            if elapsed_self_m < gap_minutes:
                remaining_m = int(gap_minutes - elapsed_self_m)
                print(f"[-] Spacing cooldown active for {acc_cfg.get('name', 'IG')}: {elapsed_self_m/60.0:.1f}h since last post. Must wait {remaining_m}m.")
                return None

        # 3. CROSS-ACCOUNT SAFEGUARD: Minimum separation between any two Instagram uploads
        if last_any_ig:
            elapsed_cross_m = (now_ist - last_any_ig).total_seconds() / 60.0
            if elapsed_cross_m < cross_gap_min:
                print(f"[-] Cross-account IG cooldown active: {elapsed_cross_m:.1f}m since last IG upload. Must wait {cross_gap_min - int(elapsed_cross_m)}m.")
                return None

    if reg_count < reg_target:
        return "regular"
    if trial_count < trial_target:
        return "trial"
    return "regular" if total_today < effective_cap else None


def check_any_platform_can_post(
    config: dict,
    platforms: list = None,
    force: bool = False,
    ig_slot: int = None,
    ig_kind: str = None
) -> tuple[bool, str, list]:
    """
    Early gatekeeper: Checks if YouTube or any Instagram account is currently eligible
    to post based on dynamic schedule (24h / posts - 30m) and cross-account gaps.
    Returns (can_post, reason_str, list_of_eligible_targets).
    """
    if platforms is None:
        platforms = ["youtube", "instagram"]
    if force:
        return True, "Force mode enabled", platforms

    logs = _load_json(TWITCH_LOG_FILE, [])
    stats = _get_today_stats(logs)
    sched = config.get("publishing_schedule", {})
    now_ist = datetime.now(IST)

    eligible = []
    cooldown_reasons = []

    # 1. YouTube Shorts check
    yt_cfg = sched.get("youtube", {"enabled": True, "shorts_per_day": 3, "hard_daily_ceiling": 3})
    if "youtube" in platforms:
        yt_posts_day = int(yt_cfg.get("shorts_per_day", 3) if yt_cfg.get("shorts_per_day") is not None else 3)
        yt_ceiling = int(yt_cfg.get("hard_daily_ceiling", yt_posts_day) if yt_cfg.get("hard_daily_ceiling") is not None else yt_posts_day)
        yt_cap = min(yt_posts_day, yt_ceiling)
        if not yt_cfg.get("enabled", True) or yt_cap <= 0:
            cooldown_reasons.append("YouTube paused (0 Shorts/day configured)")
        else:
            yt_count = stats["youtube"]["count"]
            last_yt = stats["youtube"]["last"]
            yt_gap_m = get_account_interval_minutes(yt_posts_day)

            if yt_count >= yt_cap:
                cooldown_reasons.append(f"YouTube hit daily cap ({yt_count}/{yt_cap})")
            elif last_yt and ((now_ist - last_yt).total_seconds() / 60.0) < yt_gap_m:
                elapsed_m = (now_ist - last_yt).total_seconds() / 60.0
                remaining_m = int(yt_gap_m - elapsed_m)
                cooldown_reasons.append(f"YouTube cooldown active ({elapsed_m/60.0:.1f}h/{yt_gap_m/60.0:.1f}h, {remaining_m}m remaining)")
            else:
                eligible.append("YouTube Shorts")

    # 2. Instagram accounts check
    if "instagram" in platforms:
        cross_gap = sched.get("min_cross_account_gap_minutes", 25)
        last_any_ig = max(
            [t for t in (stats["ig_1"]["last"], stats["ig_2"]["last"]) if t is not None],
            default=None,
        )
        ig_accounts = sched.get("instagram_accounts", [])
        for acc_cfg in ig_accounts:
            slot = acc_cfg.get("slot", 1)
            if ig_slot is not None and slot != ig_slot:
                continue
            suffix = "" if slot == 1 else f"_{slot}"
            meta_token = os.getenv("META_ACCESS_TOKEN")
            ig_id = os.getenv(f"INSTAGRAM_ACCOUNT_ID{suffix}") if suffix else os.getenv("INSTAGRAM_ACCOUNT_ID")
            has_meta = bool(meta_token and ig_id)
            has_instagrapi = bool(os.getenv(f"INSTA_USERNAME{suffix}") and os.getenv(f"INSTA_PASSWORD{suffix}"))
            if not (has_meta or has_instagrapi):
                continue
            if ig_kind in ("regular", "trial"):
                action = ig_kind
            else:
                action = _pick_next_ig_action(acc_cfg, stats[f"ig_{slot}"], last_any_ig, cross_gap, force=force)
            if action:
                eligible.append(f"{acc_cfg.get('name', f'IG Slot {slot}')} [{action}]")

    can_post = len(eligible) > 0
    if can_post:
        reason = f"Eligible targets ready: {', '.join(eligible)}"
    else:
        reason = f"All accounts on cooldown or cap reached ({'; '.join(cooldown_reasons) if cooldown_reasons else 'No accounts eligible'})"
    return can_post, reason, eligible


def trigger_background_clip_generation(config: dict):
    """
    Starts a new GitHub Actions runner via workflow_dispatch to generate fresh clips immediately.
    Falls back to running harvest_clips locally if GITHUB_TOKEN is not configured.
    """
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    repo = os.getenv("GITHUB_REPOSITORY")
    if token and repo:
        try:
            import urllib.request
            url = f"https://api.github.com/repos/{repo}/actions/workflows/twitch_clipper.yml/dispatches"
            payload = json.dumps({"ref": "master", "inputs": {"harvest_only": "true"}}).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "HyperClip-AI",
                    "Content-Type": "application/json",
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status in (200, 204):
                    print("[+] Successfully triggered background GitHub Actions runner for fresh clip generation.")
                    return
        except Exception as e:
            print(f"[!] Warning: Could not trigger GitHub Actions dispatch ({e}). Running local harvest...")

    # Fallback: harvest locally
    print("[*] Harvesting fresh clips for pipeline queue...")
    harvest_clips(config, max_total_new=2)


def publish_next_clip(
    config: dict,
    platforms: list = None,
    force: bool = False,
    ig_slot: int = None,
    ig_kind: str = None,
) -> dict:
    if platforms is None:
        platforms = ["youtube", "instagram"]

    sched = config.get("publishing_schedule", {})
    ig_accounts = sched.get("instagram_accounts", [])
    ig_any_enabled = any(a.get("enabled", False) for a in ig_accounts)
    if "instagram" in platforms and not ig_any_enabled:
        print("[!] NOTICE: Instagram posting is PAUSED to protect account from automated scraping flags.")
        print("[*] Continuing exclusively with YouTube Shorts.")
        platforms = [p for p in platforms if p != "instagram"]

    # Step 1: Early Gatekeeper - check timestamps & cooldowns before touching any media
    can_post, reason, eligible = check_any_platform_can_post(
        config, platforms=platforms, force=force, ig_slot=ig_slot, ig_kind=ig_kind
    )
    if not can_post:
        print("\n" + "=" * 60)
        print(f"GATEKEEPER CHECK: {reason}")
        print("[*] No account is eligible to post right now. Going back to sleep.")
        print("=" * 60)
        return {"status": "skipped", "reason": reason}

    print("\n" + "=" * 60)
    print(f"GATEKEEPER APPROVED: {reason}")
    print("[*] Checking queued clips and publishing scheduled videos...")
    print("=" * 60)

    ensure_dirs()
    enforce_storage_limits(config)

    def _clip_sort_key(cname):
        cpath = os.path.join(STREAM_PIPELINE_DIR, cname)
        mpath = os.path.join(STREAM_PIPELINE_DIR, os.path.splitext(cname)[0] + ".json")
        meta = _load_json(mpath, {})
        # 4-Tier Priority: 0=Prioritized, 1=Approved, 2=No Category, 3=Deprioritized, 9=Denied
        priority, _ = compute_clip_priority(meta, config, filename=cname)

        # Strict FIFO within each priority tier: sort by date/timestamp, never alphabetically
        raw_ts = meta.get("timestamp") or meta.get("staged_at") or meta.get("created_at")
        ts_val = 0.0
        if raw_ts:
            try:
                ts_val = datetime.fromisoformat(str(raw_ts)).timestamp()
            except Exception:
                pass
        if ts_val <= 0:
            m = re.match(r"^(\d{4}-\d{2}-\d{2})", cname)
            if m:
                try:
                    ts_val = datetime.strptime(m.group(1), "%Y-%m-%d").timestamp()
                except Exception:
                    pass
        if ts_val <= 0:
            try:
                ts_val = os.path.getmtime(cpath)
            except Exception:
                ts_val = 0.0

        return (priority, ts_val)

    queued = sorted([f for f in os.listdir(STREAM_PIPELINE_DIR) if f.endswith(".mp4")], key=_clip_sort_key)

    # Check if there are publishable clips in the pipeline
    publishable = [
        f for f in queued
        if _load_json(os.path.join(STREAM_PIPELINE_DIR, os.path.splitext(f)[0] + ".json"), {}).get("approval_status") != "denied"
    ]
    if len(publishable) == 0:
        print("[*] Pipeline empty of publishable clips. Harvesting fresh hype clips from live streams...")
        harvest_clips(config, max_total_new=3)
        queued = sorted([f for f in os.listdir(STREAM_PIPELINE_DIR) if f.endswith(".mp4")], key=_clip_sort_key)

    if not queued:
        return {"status": "empty", "reason": "No clips found in pipeline or live streams."}

    logs = _load_json(TWITCH_LOG_FILE, [])
    stats = _get_today_stats(logs)
    sched = config.get("publishing_schedule", {})
    now_ist = datetime.now(IST)

    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uploads": {},
        "upload_clip_map": {},
        "upload_captions": {},
        "clips_used": [],
    }

    def _next_clip(for_platform="instagram", ig_slot=1):
        target_tag = "youtube" if for_platform == "youtube" else f"ig_{ig_slot}"
        for cname in queued:
            cpath = os.path.join(STREAM_PIPELINE_DIR, cname)
            mpath = os.path.splitext(cpath)[0] + ".json"
            meta = _load_json(mpath, {})

            # Denied clips are never published
            if meta.get("approval_status") == "denied" or meta.get("status") == "denied":
                continue

            target_accounts = meta.get("target_accounts", [])
            target_str = str(meta.get("target", "")).lower()

            if for_platform == "youtube":
                if meta.get("posted_to_youtube", False):
                    continue
                is_assigned_yt = ("youtube" in target_accounts) or meta.get("post_to_yt", False) or ("youtube" in target_str)
                if is_assigned_yt:
                    return (cname, cpath, mpath), meta

            elif for_platform == "instagram":
                if meta.get("posted_to_instagram", False):
                    continue

                assigned_ig = meta.get("assigned_ig")
                other_slot_tag = "ig_2" if ig_slot == 1 else "ig_1"

                # Strict account isolation: NEVER steal a clip assigned specifically to the other Instagram account
                if assigned_ig == other_slot_tag:
                    continue
                if other_slot_tag in target_accounts and target_tag not in target_accounts:
                    continue

                is_assigned_this_ig = (
                    (target_tag in target_accounts) or
                    (assigned_ig == target_tag) or
                    (not assigned_ig and (
                        "instagram" in target_accounts or
                        "instagram" in target_str or
                        meta.get("post_to_ig", False)
                    ))
                )
                if is_assigned_this_ig:
                    return (cname, cpath, mpath), meta

        return (None, None, None), {}

    # 1. YouTube Shorts
    yt_cfg = sched.get("youtube", {"enabled": True, "shorts_per_day": 3, "hard_daily_ceiling": 3})
    if "youtube" in platforms and yt_cfg.get("enabled", True):
        yt_count = stats["youtube"]["count"]
        yt_posts_day = int(yt_cfg.get("shorts_per_day", 3) if yt_cfg.get("shorts_per_day") is not None else 3)
        yt_ceiling = int(yt_cfg.get("hard_daily_ceiling", yt_posts_day) if yt_cfg.get("hard_daily_ceiling") is not None else yt_posts_day)
        yt_cap = min(yt_posts_day, yt_ceiling)
        last_yt = stats["youtube"]["last"]
        yt_gap_m = get_account_interval_minutes(yt_posts_day)

        if yt_cap <= 0:
            print("[-] YouTube Shorts set to 0 posts/day (Paused). Refusing to post.")
            yt_ok = False
        elif yt_count >= yt_cap:
            print(f"[-] Hard daily ceiling reached for YouTube ({yt_count}/{yt_cap} today). Refusing to post.")
            yt_ok = False
        elif last_yt and ((now_ist - last_yt).total_seconds() / 60.0) < yt_gap_m:
            elapsed_yt_m = (now_ist - last_yt).total_seconds() / 60.0
            remaining_m = int(yt_gap_m - elapsed_yt_m)
            print(f"[-] YouTube cooldown active: {elapsed_yt_m/60.0:.1f}h since last Short. Must wait {remaining_m}m.")
            yt_ok = False
        else:
            yt_ok = True

        if yt_ok:
            clip_info, meta = _next_clip(for_platform="youtube")
            if not clip_info[0]:
                print("[*] No clips currently scheduled for YouTube Shorts in pipeline. Harvesting fresh clips...")
                harvest_clips(config, max_total_new=2)
                queued = sorted([f for f in os.listdir(STREAM_PIPELINE_DIR) if f.endswith(".mp4")], key=_clip_sort_key)
                clip_info, meta = _next_clip(for_platform="youtube")

            if clip_info[0]:
                cname, cpath, _ = clip_info
                title = meta.get("title", cname.replace(".mp4", "").replace("_", " ").title())
                caption = meta.get("caption", f"{title} #shorts #twitch #gaming")
                try:
                    yt_url = upload_short(
                        cpath,
                        title=title,
                        description=caption,
                        tags=["shorts", "gaming", "gta6", "twitch", "clips"],
                        category_id="20",
                        title_suffix="#Shorts",
                    )
                    results["uploads"]["youtube"] = yt_url
                    results["upload_clip_map"]["youtube"] = cname
                    results["upload_captions"]["youtube"] = caption
                    results["clips_used"].append(cname)
                except Exception as e:
                    print(f"[-] YouTube upload error: {e}")
                    results["uploads"]["youtube"] = f"Failed: {e}"
            else:
                print("[-] No clips available for YouTube Shorts. Skipping YouTube this run.")

    # 2. Instagram Accounts (Enforce Rule 7: Two Instagram posts cannot be made at the same time)
    if "instagram" in platforms:
        cross_gap = sched.get("min_cross_account_gap_minutes", 25)
        last_any_ig = max(
            [t for t in (stats["ig_1"]["last"], stats["ig_2"]["last"]) if t is not None],
            default=None,
        )

        ig_accounts = sched.get("instagram_accounts", [])
        # Prioritize the account that has gone the longest without posting
        def _acc_sort_priority(acc):
            slot = acc.get("slot", 1)
            last_dt = stats[f"ig_{slot}"]["last"]
            return last_dt.timestamp() if last_dt else 0.0

        sorted_ig_accounts = sorted(ig_accounts, key=_acc_sort_priority)

        for acc_cfg in sorted_ig_accounts:
            slot = acc_cfg.get("slot", 1)
            if ig_slot is not None and slot != ig_slot:
                continue
            suffix = "" if slot == 1 else f"_{slot}"
            meta_token = os.getenv("META_ACCESS_TOKEN")
            ig_id = os.getenv(f"INSTAGRAM_ACCOUNT_ID{suffix}") if suffix else os.getenv("INSTAGRAM_ACCOUNT_ID")
            has_meta = bool(meta_token and ig_id)
            has_instagrapi = bool(os.getenv(f"INSTA_USERNAME{suffix}") and os.getenv(f"INSTA_PASSWORD{suffix}"))
            if not (has_meta or has_instagrapi):
                continue

            if ig_kind in ("regular", "trial"):
                action_kind = ig_kind
            else:
                action_kind = _pick_next_ig_action(acc_cfg, stats[f"ig_{slot}"], last_any_ig, cross_gap, force)
            if not action_kind:
                continue

            clip_info, meta = _next_clip(for_platform="instagram", ig_slot=slot)
            if not clip_info[0]:
                print(f"[*] No queued clips available for Instagram Slot {slot}. Harvesting fresh clips...")
                harvest_clips(config, max_total_new=2)
                queued = sorted([f for f in os.listdir(STREAM_PIPELINE_DIR) if f.endswith(".mp4")], key=_clip_sort_key)
                clip_info, meta = _next_clip(for_platform="instagram", ig_slot=slot)

            if not clip_info[0]:
                print(f"[-] Still no clips available for Instagram Slot {slot}. Skipping.")
                continue

            cname, cpath, _ = clip_info
            title = meta.get("title", cname.replace(".mp4", "").replace("_", " ").title())
            caption = meta.get("caption", f"{title} #reels #twitch #gaming")

            try:
                permalink = upload_reel(cpath, caption, account_slot=slot, trial=(action_kind == "trial"))
                results["uploads"][f"instagram_{slot}_{action_kind}"] = permalink
                results["upload_clip_map"][f"instagram_{slot}_{action_kind}"] = cname
                results["upload_captions"][f"instagram_{slot}_{action_kind}"] = caption
                results["clips_used"].append(cname)
                # Rule 7: Only 1 Instagram upload per runner execution (minimum cross-account separation)
                break
            except Exception as e:
                print(f"[-] Instagram (slot {slot}, {action_kind}) upload error: {e}")
                results["uploads"][f"instagram_{slot}_{action_kind}"] = f"Failed: {e}"

    # Step 3: Lifecycle Management (Tag Removal, 7-Day Retention & Moving to stream_posted/)
    has_success = any(isinstance(v, str) and not v.lower().startswith("failed") for v in results["uploads"].values())
    if has_success:
        logs.append(results)
        _save_json(TWITCH_LOG_FILE, logs)

        yt_posted_cnames = [c for c in results.get("clips_used", []) if "youtube" in results.get("uploads", {})]
        ig_posted_cnames = [c for c in results.get("clips_used", []) if any(k.startswith("instagram_") for k in results.get("uploads", {}))]

        for cname in set(results["clips_used"]):
            cpath = os.path.join(STREAM_PIPELINE_DIR, cname)
            mpath = os.path.splitext(cpath)[0] + ".json"
            meta = _load_json(mpath, {})

            targets = list(meta.get("target_accounts", []))

            if cname in yt_posted_cnames:
                meta["posted_to_youtube"] = True
                meta["youtube_url"] = results["uploads"].get("youtube", "")
                if "youtube" in targets:
                    targets.remove("youtube")

            if cname in ig_posted_cnames:
                meta["posted_to_instagram"] = True
                for k, url in results["uploads"].items():
                    if k.startswith("instagram_"):
                        meta["instagram_url"] = url
                # Remove Instagram target
                assigned_ig = meta.get("assigned_ig", "ig_1")
                if assigned_ig in targets:
                    targets.remove(assigned_ig)
                elif "ig_1" in targets:
                    targets.remove("ig_1")
                elif "ig_2" in targets:
                    targets.remove("ig_2")

            meta["target_accounts"] = targets
            _save_json(mpath, meta)

            # Check if all assigned destinations are complete
            if len(targets) == 0:
                # Move to stream_posted/ to preserve for 7 days
                posted_mp4 = os.path.join(STREAM_POSTED_DIR, cname)
                posted_json = os.path.join(STREAM_POSTED_DIR, os.path.splitext(cname)[0] + ".json")
                if os.path.exists(cpath):
                    shutil.move(cpath, posted_mp4)
                if os.path.exists(mpath):
                    shutil.move(mpath, posted_json)
                print(f"[+] Clip '{cname}' completed all assigned destinations -> Moved to stream_posted/ (Retained for 7 days).")
            else:
                remaining_desc = ", ".join(targets)
                print(f"[*] Clip '{cname}' retained in stream_pipeline/ for remaining destination: {remaining_desc}")

        # When a video is posted, trigger a new runner immediately to generate fresh clips
        print("[*] Video upload complete. Triggering background runner to generate next clips...")
        trigger_background_clip_generation(config)
    else:
        print("[*] No eligible publishing slots right now (cooldown/daily cap active).")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HyperClip AI - Twitch Hype Clipper")
    parser.add_argument("--harvest-only", action="store_true", help="Only scan and stage clips without posting")
    parser.add_argument("--check-only", action="store_true", help="Check live/VOD targets and exit")
    parser.add_argument("--force", action="store_true", help="Bypass daily cap and cooldown")
    parser.add_argument("--platforms", nargs="+", default=["youtube", "instagram"])
    parser.add_argument("--ig-slot", type=int, default=None, help="Target a specific IG account slot (1 or 2)")
    parser.add_argument("--ig-kind", choices=["auto", "regular", "trial"], default="auto", help="Force IG post type")
    args = parser.parse_args()

    cfg = load_config()
    if args.check_only:
        t = find_clippable_targets(cfg)
        print(json.dumps(t, indent=2))
    elif args.harvest_only:
        harvest_clips(cfg)
    else:
        kind_arg = None if args.ig_kind == "auto" else args.ig_kind
        publish_next_clip(cfg, platforms=args.platforms, force=args.force, ig_slot=args.ig_slot, ig_kind=kind_arg)
