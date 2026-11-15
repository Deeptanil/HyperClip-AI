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
from src.uploaders.youtube_uploader import upload_short
from src.uploaders.instagram_uploader import upload_reel_direct

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
                facecam_box = detect_facecam_region(raw_clip, raw_w, raw_h)

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
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                _save_json(out_json, meta)
                already_clipped.append(peak)
                staged_clips.append(out_mp4)
                print(f"[+] Staged Twitch clip: {out_mp4} (hook='{hook_headline}', z={m['z_score']})")
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


def _pick_next_ig_action(acc_cfg: dict, acc_stats: dict, last_any_ig: datetime | None, cross_gap_min: int, force: bool = False) -> str | None:
    """
    Returns 'regular', 'trial', or None for an Instagram account slot.
    Enforces strict hard limits to protect accounts from shadowbans:
    - Never exceeds hard_daily_ceiling (default 3, max 4) under ANY circumstances.
    - Never violates cross-account gap (20 mins) or per-account cooldown (min_gap_hours).
    """
    if not acc_cfg.get("enabled", True):
        return None

    now_ist = datetime.now(IST)
    reg_count = acc_stats.get("regular", 0)
    trial_count = acc_stats.get("trial", 0)
    total_today = reg_count + trial_count
    hard_ceiling = acc_cfg.get("hard_daily_ceiling", acc_cfg.get("regular_per_day", 2) + acc_cfg.get("trial_per_day", 2))

    # HARD CEILING: Under no condition can an account exceed this ceiling in 24 hours
    if total_today >= hard_ceiling:
        print(f"[-] Hard daily ceiling reached for {acc_cfg.get('name', 'IG')} ({total_today}/{hard_ceiling} today). Refusing to post.")
        return None

    # MINIMUM SPACING COOLDOWN: Never post within min_gap_hours of previous post on same account
    last_self = acc_stats.get("last")
    min_gap_h = float(acc_cfg.get("min_gap_hours", 3.0))
    if last_self:
        elapsed_self_h = (now_ist - last_self).total_seconds() / 3600.0
        if elapsed_self_h < min_gap_h:
            remaining_m = int((min_gap_h - elapsed_self_h) * 60)
            print(f"[-] Spacing cooldown active for {acc_cfg.get('name', 'IG')}: {elapsed_self_h:.1f}h since last post. Must wait {remaining_m}m.")
            return None

    # CROSS-ACCOUNT SAFEGUARD: Minimum separation between different accounts from same IP
    if last_any_ig:
        elapsed_cross_m = (now_ist - last_any_ig).total_seconds() / 60.0
        if elapsed_cross_m < cross_gap_min:
            print(f"[-] Cross-account cooldown active: {elapsed_cross_m:.1f}m since last IG upload. Must wait {cross_gap_min - int(elapsed_cross_m)}m.")
            return None

    if reg_count < acc_cfg.get("regular_per_day", 2):
        return "regular"
    if trial_count < acc_cfg.get("trial_per_day", 2):
        return "trial"
    return None


def check_any_platform_can_post(
    config: dict,
    platforms: list = None,
    force: bool = False,
    ig_slot: int = None,
    ig_kind: str = None
) -> tuple[bool, str, list]:
    """
    Early gatekeeper: Checks if YouTube or any Instagram account is currently eligible
    to post (i.e. not on cooldown and not exceeding daily ceilings).
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
    yt_cfg = sched.get("youtube", {"enabled": True, "shorts_per_day": 3, "min_gap_hours": 3.0, "hard_daily_ceiling": 3})
    if "youtube" in platforms and yt_cfg.get("enabled", True):
        yt_count = stats["youtube"]["count"]
        yt_ceiling = yt_cfg.get("hard_daily_ceiling", yt_cfg.get("shorts_per_day", 3))
        last_yt = stats["youtube"]["last"]
        min_yt_gap = float(yt_cfg.get("min_gap_hours", 3.0))

        if yt_count >= yt_ceiling:
            cooldown_reasons.append(f"YouTube hit daily cap ({yt_count}/{yt_ceiling})")
        elif last_yt and ((now_ist - last_yt).total_seconds() / 3600.0) < min_yt_gap:
            elapsed_h = (now_ist - last_yt).total_seconds() / 3600.0
            remaining_m = int((min_yt_gap - elapsed_h) * 60)
            cooldown_reasons.append(f"YouTube cooldown active ({elapsed_h:.1f}h/{min_yt_gap}h, {remaining_m}m remaining)")
        else:
            eligible.append("YouTube Shorts")

    # 2. Instagram accounts check
    if "instagram" in platforms:
        cross_gap = sched.get("min_cross_account_gap_minutes", 20)
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
            if not (os.getenv(f"INSTA_USERNAME{suffix}") and os.getenv(f"INSTA_PASSWORD{suffix}")):
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


def publish_next_clip(
    config: dict,
    platforms: list = None,
    force: bool = False,
    ig_slot: int = None,
    ig_kind: str = None,
) -> dict:
    if platforms is None:
        platforms = ["youtube", "instagram"]

    # First check: Can any account post right now? If no, don't do anything and go back to sleep!
    can_post, reason, eligible = check_any_platform_can_post(
        config, platforms=platforms, force=force, ig_slot=ig_slot, ig_kind=ig_kind
    )
    if not can_post:
        print("\n" + "=" * 60)
        print(f"😴 GATEKEEPER CHECK: {reason}")
        print("[*] No account is eligible to post right now. Going back to sleep.")
        print("=" * 60)
        return {"status": "skipped", "reason": reason}

    print("\n" + "=" * 60)
    print(f"🚀 GATEKEEPER APPROVED: {reason}")
    print("[*] Proceeding with video staging, pipeline check, and publication...")
    print("=" * 60)

    ensure_dirs()
    enforce_storage_limits(config)

    queued = sorted([f for f in os.listdir(STREAM_PIPELINE_DIR) if f.endswith(".mp4")])
    if len(queued) < 4:
        print("[*] Harvesting fresh hype clips to keep multi-account queue stocked...")
        harvest_clips(config, max_total_new=4)
        queued = sorted([f for f in os.listdir(STREAM_PIPELINE_DIR) if f.endswith(".mp4")])

    if not queued:
        return {"status": "empty", "reason": "No clips found in pipeline or live streams."}

    logs = _load_json(TWITCH_LOG_FILE, [])
    stats = _get_today_stats(logs)
    sched = config.get("publishing_schedule", {})
    now_ist = datetime.now(IST)

    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uploads": {},
        "clips_used": [],
    }

    clip_idx = 0

    def _next_clip():
        nonlocal clip_idx
        while clip_idx < len(queued):
            cname = queued[clip_idx]
            clip_idx += 1
            cpath = os.path.join(STREAM_PIPELINE_DIR, cname)
            mpath = os.path.splitext(cpath)[0] + ".json"
            meta = _load_json(mpath, {})

            # Denied clips are never published (approval is optional, but denial is respected)
            if meta.get("approval_status") == "denied" or meta.get("status") == "denied":
                print(f"[-] Skipping explicitly denied clip: {cname}")
                continue

            return (cname, cpath, mpath), meta
        return (None, None, None), {}

    # 1. YouTube Shorts
    yt_cfg = sched.get("youtube", {"enabled": True, "shorts_per_day": 3, "min_gap_hours": 3.0, "hard_daily_ceiling": 3})
    if "youtube" in platforms and yt_cfg.get("enabled", True):
        yt_count = stats["youtube"]["count"]
        yt_ceiling = yt_cfg.get("hard_daily_ceiling", yt_cfg.get("shorts_per_day", 3))
        last_yt = stats["youtube"]["last"]
        min_yt_gap = float(yt_cfg.get("min_gap_hours", 3.0))

        if yt_count >= yt_ceiling:
            print(f"[-] Hard daily ceiling reached for YouTube ({yt_count}/{yt_ceiling} today). Refusing to post.")
            yt_ok = False
        elif last_yt and ((now_ist - last_yt).total_seconds() / 3600.0) < min_yt_gap:
            elapsed_yt_h = (now_ist - last_yt).total_seconds() / 3600.0
            remaining_m = int((min_yt_gap - elapsed_yt_h) * 60)
            print(f"[-] YouTube cooldown active: {elapsed_yt_h:.1f}h since last Short. Must wait {remaining_m}m.")
            yt_ok = False
        else:
            yt_ok = True
        if yt_ok:
            clip_info, meta = _next_clip()
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
                    results["clips_used"].append(cname)
                except Exception as e:
                    print(f"[-] YouTube upload error: {e}")
                    results["uploads"]["youtube"] = f"Failed: {e}"

    # 2. Instagram Accounts (Slot 1 & Slot 2, Regular & Trial Reels, spaced safely)
    if "instagram" in platforms:
        cross_gap = sched.get("min_cross_account_gap_minutes", 20)
        last_any_ig = max(
            [t for t in (stats["ig_1"]["last"], stats["ig_2"]["last"]) if t is not None],
            default=None,
        )

        ig_accounts = sched.get("instagram_accounts", [])
        # Prioritize accounts that haven't posted recently or missed an upload to catch up fairly
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
            if not (os.getenv(f"INSTA_USERNAME{suffix}") and os.getenv(f"INSTA_PASSWORD{suffix}")):
                continue

            if ig_kind in ("regular", "trial"):
                action_kind = ig_kind
            else:
                action_kind = _pick_next_ig_action(acc_cfg, stats[f"ig_{slot}"], last_any_ig, cross_gap, force)
            if not action_kind:
                continue

            clip_info, meta = _next_clip()
            if not clip_info[0]:
                break
            cname, cpath, _ = clip_info
            title = meta.get("title", cname.replace(".mp4", "").replace("_", " ").title())
            caption = meta.get("caption", f"{title} #reels #twitch #gaming")

            try:
                code = upload_reel_direct(cpath, caption, account_slot=slot, trial=(action_kind == "trial"))
                results["uploads"][f"instagram_{slot}_{action_kind}"] = f"https://instagram.com/reel/{code}"
                results["clips_used"].append(cname)
                last_any_ig = datetime.now(IST)
                break  # At most 1 IG account per 30-min cycle to prevent same-IP dual-login flags
            except Exception as e:
                print(f"[-] Instagram (slot {slot}, {action_kind}) upload error: {e}")
                results["uploads"][f"instagram_{slot}_{action_kind}"] = f"Failed: {e}"

    if any(isinstance(v, str) and not v.lower().startswith("failed") for v in results["uploads"].values()):
        logs.append(results)
        _save_json(TWITCH_LOG_FILE, logs)
        for cname in set(results["clips_used"]):
            src_mp4 = os.path.join(STREAM_PIPELINE_DIR, cname)
            src_json = os.path.splitext(src_mp4)[0] + ".json"
            if os.path.exists(src_mp4):
                shutil.move(src_mp4, os.path.join(STREAM_POSTED_DIR, cname))
            if os.path.exists(src_json):
                shutil.move(src_json, os.path.join(STREAM_POSTED_DIR, os.path.basename(src_json)))
        print(f"[+] Archived {len(set(results['clips_used']))} posted clip(s) to {STREAM_POSTED_DIR}")
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
