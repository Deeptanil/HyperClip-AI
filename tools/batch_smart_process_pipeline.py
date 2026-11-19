"""
Batch Smart Editing & Censorship Processor for Stream Pipeline Clips.
Applies:
1. Smart Dead-Air & Silence Fast-Forwarding (3.0x speedup on pauses/reading chat/phone).
2. Profanity detection via faster-whisper and 1000Hz audio bleeping.
3. NSFW / sexual content visual scanning and blur censorship.
4. Updates JSON metadata for dashboard and scheduler tracking.
"""

import os
import sys
import glob
import json
import shutil
import tempfile
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.twitch_clipper.smart_editor import (
    fast_forward_dead_air,
    apply_audio_bleeping,
    get_video_duration
)
from src.twitch_clipper.captioner import generate_clip_captions
from src.twitch_clipper.nsfw_censor import scan_and_censor_nsfw


def process_pipeline_clip(video_path: str, meta_path: str | None = None, work_dir: str = "temp_pipeline_edit") -> dict:
    """Processes a single pipeline clip through smart dead-air fast-forward, profanity bleeping, and NSFW censorship."""
    os.makedirs(work_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    orig_dur = get_video_duration(video_path)
    
    print(f"\n==================================================")
    print(f"[*] Processing: {base_name}")
    print(f"[*] Original duration: {orig_dur:.2f}s")
    print(f"==================================================")

    tmp_ff = os.path.join(work_dir, f"{base_name}_ff.mp4")
    tmp_bleep = os.path.join(work_dir, f"{base_name}_bleep.mp4")
    tmp_ass = os.path.join(work_dir, f"{base_name}.ass")

    working_video = video_path
    ff_segments = []
    bleep_segments = []
    nsfw_info = {"action": "clean", "segments": []}

    # 1. Dead-Air Fast Forwarding
    try:
        res_vid, segs = fast_forward_dead_air(
            input_video_path=video_path,
            output_video_path=tmp_ff,
            speed_multiplier=3.0,
            min_pause_sec=1.3,
            max_motion_threshold=22.0,
            show_badge=True
        )
        if segs and res_vid != video_path and os.path.exists(res_vid):
            working_video = res_vid
            ff_segments = segs
            dur_after_ff = get_video_duration(working_video)
            print(f"[+] Dead-air fast-forward applied: {len(segs)} pauses ({orig_dur:.1f}s -> {dur_after_ff:.1f}s)")
        else:
            print("[-] No qualifying dead-air pauses found; keeping 1x speed.")
    except Exception as e:
        print(f"[!] Fast-forward error on {base_name}: {e}")

    # 2. Profanity Detection & Audio Bleeping
    try:
        ass_path, bleeps = generate_clip_captions(working_video, tmp_ass, censor_profanity=True)
        if bleeps:
            ok_bleep = apply_audio_bleeping(working_video, tmp_bleep, bleeps)
            if ok_bleep and os.path.exists(tmp_bleep):
                working_video = tmp_bleep
                bleep_segments = bleeps
                print(f"[+] Audio bleeped {len(bleeps)} profanity segment(s).")
        else:
            print("[-] No profanity detected in audio.")
    except Exception as e:
        print(f"[!] Profanity detection error on {base_name}: {e}")

    # 3. NSFW Visual Scanning & Censorship
    try:
        nsfw_info = scan_and_censor_nsfw(working_video, censor_mode="blur")
        print(f"[*] NSFW scan result: {nsfw_info.get('action', 'clean')}")
    except Exception as e:
        print(f"[!] NSFW scan error on {base_name}: {e}")

    # 4. Overwrite original MP4 atomically if modified
    final_dur = get_video_duration(working_video)
    if working_video != video_path:
        shutil.copy2(working_video, video_path)
        print(f"[+] Replaced pipeline clip {video_path} with edited version.")

    # 5. Update Metadata JSON
    if meta_path and os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            
            meta["duration_sec"] = round(final_dur, 2)
            meta["smart_edited"] = True
            meta["fast_forward_segments"] = ff_segments
            meta["profanity_bleeped"] = bool(bleep_segments)
            meta["bleep_segments"] = bleep_segments
            meta["nsfw_censored"] = nsfw_info.get("action") == "censored"
            meta["nsfw_segments"] = nsfw_info.get("segments", [])

            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)
            print(f"[+] Updated metadata: {meta_path}")
        except Exception as e:
            print(f"[!] Metadata update error on {meta_path}: {e}")

    # 6. Clean up temporary files
    for p in [tmp_ff, tmp_bleep, tmp_ass]:
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass

    return {
        "clip": base_name,
        "original_dur": orig_dur,
        "final_dur": final_dur,
        "saved_sec": round(orig_dur - final_dur, 2),
        "ff_count": len(ff_segments),
        "bleep_count": len(bleep_segments),
        "nsfw_status": nsfw_info.get("action", "clean")
    }


def main():
    pipeline_dir = os.path.join(ROOT_DIR, "output", "stream_pipeline")
    mp4_files = sorted(glob.glob(os.path.join(pipeline_dir, "*.mp4")))
    
    if not mp4_files:
        print(f"[!] No mp4 files found in {pipeline_dir}")
        return

    print(f"[*] Found {len(mp4_files)} clips in pipeline to process.")
    work_dir = os.path.join(ROOT_DIR, "temp_pipeline_edit")
    os.makedirs(work_dir, exist_ok=True)

    summary = []
    for mp4 in mp4_files:
        json_path = os.path.splitext(mp4)[0] + ".json"
        if not os.path.exists(json_path):
            json_path = None
        info = process_pipeline_clip(mp4, json_path, work_dir=work_dir)
        summary.append(info)

    # Clean up work directory
    try:
        shutil.rmtree(work_dir, ignore_errors=True)
    except Exception:
        pass

    print("\n" + "=" * 80)
    print("BATCH PROCESSING COMPLETED - SUMMARY REPORT")
    print("=" * 80)
    print(f"{'CLIP NAME':<40} | {'ORIG':<6} | {'NEW':<6} | {'SAVED':<6} | {'FF':<3} | {'BLEEP':<5} | {'NSFW'}")
    print("-" * 80)
    total_saved = 0.0
    total_ff = 0
    total_bleeps = 0
    for s in summary:
        print(f"{s['clip'][:38]:<40} | {s['original_dur']:>5.1f}s | {s['final_dur']:>5.1f}s | {s['saved_sec']:>5.1f}s | {s['ff_count']:>3} | {s['bleep_count']:>5} | {s['nsfw_status']}")
        total_saved += s['saved_sec']
        total_ff += s['ff_count']
        total_bleeps += s['bleep_count']
    print("-" * 80)
    print(f"TOTALS: {len(summary)} clips processed | {total_saved:.1f}s dead-air saved | {total_ff} pauses accelerated | {total_bleeps} profanities bleeped")
    print("=" * 80)


if __name__ == "__main__":
    main()
