"""
HyperClip AI - Automated NSFW / Sexual Content Detector & Auto-Censorer.
Protects YouTube Shorts & Instagram Reels accounts from community guideline strikes:
1. Samples keyframes at 1 fps into a compact timestamped storyboard contact sheet.
2. Uses Gemini Vision (via GEMINI_API_KEY) to detect exact [start_sec, end_sec] windows
   containing nudity, strip clubs, sexual acts, lap dances, or explicit scenes.
3. Automatically censors detected segments via FFmpeg:
   - 'blur'   : Heavy privacy blur + dark overlay + "CENSORED" badge during unsafe timestamps
   - 'cut'    : Cleanly splices out unsafe timestamps (video + audio)
   - 'reject' : Rejects the entire clip so it is never queued or uploaded
"""

import os
import json
import math
import subprocess
import tempfile
import cv2
import numpy as np

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

from src.twitch_clipper.hook_generator import _get_configured_models


def _build_timestamped_storyboard(video_path: str, sample_interval_sec: float = 1.0, cols: int = 6) -> tuple[bytes | None, float]:
    """
    Extracts 1 frame every `sample_interval_sec` seconds, stamps bold timestamps
    on each thumbnail, and tiles them into a single JPEG contact sheet.
    Returns (jpeg_bytes, duration_sec).
    """
    if not os.path.exists(video_path):
        return None, 0.0

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if total_frames <= 0 or fps <= 0:
        cap.release()
        return None, 0.0

    duration = total_frames / fps
    thumb_w, thumb_h = 320, 180
    frames = []

    t = 0.0
    max_samples = 60  # Cap at 60 frames to keep grid crisp & readable
    step = max(sample_interval_sec, duration / max_samples) if duration > max_samples else sample_interval_sec

    while t < duration and len(frames) < max_samples:
        frame_idx = min(total_frames - 1, int(t * fps))
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ok, frame = cap.read()
        if ok and frame is not None:
            resized = cv2.resize(frame, (thumb_w, thumb_h), interpolation=cv2.INTER_AREA)
            label = f"{t:04.1f}s"
            cv2.rectangle(resized, (4, 4), (92, 30), (0, 0, 0), -1)
            cv2.putText(
                resized,
                label,
                (10, 24),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 255, 255),
                2,
                cv2.LINE_AA,
            )
            frames.append(resized)
        t += step

    cap.release()
    if not frames:
        return None, duration

    rows = math.ceil(len(frames) / cols)
    grid = np.zeros((rows * thumb_h, cols * thumb_w, 3), dtype=np.uint8)
    for idx, tile in enumerate(frames):
        r = idx // cols
        c = idx % cols
        grid[r * thumb_h : (r + 1) * thumb_h, c * thumb_w : (c + 1) * thumb_w] = tile

    ok, buf = cv2.imencode(".jpg", grid, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
    if not ok:
        return None, duration

    return buf.tobytes(), duration


def _merge_segments(segments: list[dict], duration: float, pad_sec: float = 0.6) -> list[dict]:
    """Pads each detected segment by ±pad_sec and merges overlapping/adjacent ranges."""
    cleaned = []
    for seg in segments:
        try:
            s = max(0.0, float(seg.get("start_sec", 0.0)) - pad_sec)
            e = min(duration, float(seg.get("end_sec", 0.0)) + pad_sec)
            if e <= s:
                e = min(duration, s + 1.5)
            cleaned.append({
                "start_sec": round(s, 2),
                "end_sec": round(e, 2),
                "reason": str(seg.get("reason", "NSFW / sexual content")),
            })
        except Exception:
            continue

    if not cleaned:
        return []

    cleaned.sort(key=lambda x: x["start_sec"])
    merged = [cleaned[0]]
    for cur in cleaned[1:]:
        prev = merged[-1]
        if cur["start_sec"] <= prev["end_sec"] + 0.5:
            prev["end_sec"] = max(prev["end_sec"], cur["end_sec"])
            if cur["reason"] not in prev["reason"]:
                prev["reason"] = f"{prev['reason']}; {cur['reason']}"
        else:
            merged.append(cur)
    return merged


def detect_nsfw_segments(video_path: str) -> dict:
    """
    Analyzes a video storyboard using Gemini Vision to detect sexual/NSFW segments.
    Returns:
      {
        "has_nsfw": bool,
        "segments": [{"start_sec": float, "end_sec": float, "reason": str}],
        "duration_sec": float,
        "blocked_by_safety": bool,
        "model": str | None,
      }
    """
    jpeg_bytes, duration = _build_timestamped_storyboard(video_path, sample_interval_sec=1.0)
    if not jpeg_bytes or duration <= 0:
        return {
            "has_nsfw": False,
            "segments": [],
            "duration_sec": duration,
            "blocked_by_safety": False,
            "model": None,
        }

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or not genai:
        print("[*] NSFW Censor: No GEMINI_API_KEY configured; skipping vision scan.")
        return {
            "has_nsfw": False,
            "segments": [],
            "duration_sec": duration,
            "blocked_by_safety": False,
            "model": None,
        }

    prompt = f"""
You are a strict YouTube Shorts & Instagram Reels Trust & Safety content moderator.
Inspect this timestamped video storyboard grid (video duration: {duration:.1f} seconds).
Each tile has its exact yellow timestamp (e.g., 04.0s, 05.0s) in the top-left corner.

Identify ANY timestamp ranges containing content that could get a gaming shorts channel banned or restricted for sexual/adult content:
- Full or partial nudity (exposed breasts, buttocks, genitalia, lingerie/bikini strip club scenes)
- Sexual acts, lap dances, pole dancing, explicit twerking, strip club interiors (e.g. GTA 6 / GTA V strip clubs, bedroom cutscenes, sexual physics)
- Sexually explicit memes, popups, or suggestive adult animations

Do NOT flag normal video game violence, car chases, gunfights, normal clothed characters, or streamer facecam reactions.

Return strictly valid JSON matching this schema:
{{
  "has_nsfw": boolean,
  "segments": [
    {{
      "start_sec": float,
      "end_sec": float,
      "reason": "brief reason (e.g. strip club nudity / sexual cutscene)"
    }}
  ]
}}
"""

    # Use configured model cascade in exact priority order
    models_to_try = _get_configured_models()

    safety_settings = [
        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_NONE),
    ]

    client = None
    for model_name in models_to_try:
        try:
            if client is None:
                client = genai.Client(api_key=api_key)
            resp = client.models.generate_content(
                model=model_name,
                contents=[
                    types.Part.from_bytes(data=jpeg_bytes, mime_type="image/jpeg"),
                    prompt,
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1,
                    max_output_tokens=300,
                    safety_settings=safety_settings,
                ),
            )

            # Check if Gemini hard-blocked the image for explicit content
            if resp.prompt_feedback and getattr(resp.prompt_feedback, "block_reason", None):
                block_reason = str(resp.prompt_feedback.block_reason)
                if "NONE" not in block_reason.upper():
                    print(f"[!] NSFW Censor: Gemini hard-blocked storyboard ({block_reason}) -> treating clip as NSFW.")
                    return {
                        "has_nsfw": True,
                        "segments": [{"start_sec": 0.0, "end_sec": round(duration, 2), "reason": f"Safety block: {block_reason}"}],
                        "duration_sec": duration,
                        "blocked_by_safety": True,
                        "model": model_name,
                    }

            raw_text = (resp.text or "").strip()
            if not raw_text:
                continue

            data = json.loads(raw_text)
            has_nsfw = bool(data.get("has_nsfw", False))
            raw_segments = data.get("segments", []) if isinstance(data.get("segments"), list) else []
            merged = _merge_segments(raw_segments, duration) if has_nsfw else []

            return {
                "has_nsfw": bool(merged),
                "segments": merged,
                "duration_sec": duration,
                "blocked_by_safety": False,
                "model": model_name,
            }
        except Exception as e:
            err_str = str(e).upper()
            if "PROHIBITED_CONTENT" in err_str or "SEXUALLY_EXPLICIT" in err_str:
                print(f"[!] NSFW Censor: Model '{model_name}' flagged prohibited content -> rejecting clip.")
                return {
                    "has_nsfw": True,
                    "segments": [{"start_sec": 0.0, "end_sec": round(duration, 2), "reason": "Prohibited explicit content"}],
                    "duration_sec": duration,
                    "blocked_by_safety": True,
                    "model": model_name,
                }
            print(f"[!] NSFW Censor model '{model_name}' failed ({e}); trying next...")

    return {
        "has_nsfw": False,
        "segments": [],
        "duration_sec": duration,
        "blocked_by_safety": False,
        "model": None,
    }


def apply_blur_censor(input_path: str, output_path: str, segments: list[dict]) -> bool:
    """
    Applies heavy privacy boxblur + dark dim + 'CENSORED' banner strictly during
    detected NSFW timestamp windows using FFmpeg, keeping audio intact.
    """
    if not segments:
        return False

    enable_expr = "+".join(
        f"between(t,{seg['start_sec']:.2f},{seg['end_sec']:.2f})" for seg in segments
    )

    # Heavy blur + dim + CENSORED center box during unsafe intervals only
    vf = (
        f"boxblur=luma_radius=40:luma_power=4:chroma_radius=20:chroma_power=2:enable='{enable_expr}',"
        f"drawbox=x=0:y=0:w=iw:h=ih:color=black@0.45:t=fill:enable='{enable_expr}',"
        f"drawtext=text='CENSORED':fontcolor=yellow:fontsize=h/10:"
        f"box=1:boxcolor=black@0.85:boxborderw=18:"
        f"x=(w-text_w)/2:y=(h-text_h)/2:enable='{enable_expr}'"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-c:a", "copy",
        "-movflags", "+faststart",
        output_path,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        # Fallback without drawtext (in case libfreetype isn't built into ffmpeg)
        vf_fallback = (
            f"boxblur=luma_radius=40:luma_power=4:chroma_radius=20:chroma_power=2:enable='{enable_expr}',"
            f"drawbox=x=0:y=0:w=iw:h=ih:color=black@0.55:t=fill:enable='{enable_expr}'"
        )
        cmd_fb = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", vf_fallback,
            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-c:a", "copy",
            "-movflags", "+faststart",
            output_path,
        ]
        res_fb = subprocess.run(cmd_fb, capture_output=True, text=True)
        return res_fb.returncode == 0
    return True


def apply_cut_censor(input_path: str, output_path: str, segments: list[dict], duration: float) -> bool:
    """
    Cuts out unsafe timestamp ranges and concatenates the remaining safe segments
    (both video and audio).
    """
    safe_ranges = []
    cursor = 0.0
    for seg in segments:
        if seg["start_sec"] > cursor + 0.25:
            safe_ranges.append((cursor, seg["start_sec"]))
        cursor = max(cursor, seg["end_sec"])
    if duration > cursor + 0.25:
        safe_ranges.append((cursor, duration))

    total_safe = sum(e - s for s, e in safe_ranges)
    if not safe_ranges or total_safe < 5.0:
        return False

    filter_parts = []
    concat_inputs = []
    for idx, (s, e) in enumerate(safe_ranges):
        filter_parts.append(f"[0:v]trim=start={s:.2f}:end={e:.2f},setpts=PTS-STARTPTS[v{idx}];")
        filter_parts.append(f"[0:a]atrim=start={s:.2f}:end={e:.2f},asetpts=PTS-STARTPTS[a{idx}];")
        concat_inputs.append(f"[v{idx}][a{idx}]")

    fc = "".join(filter_parts) + f"{''.join(concat_inputs)}concat=n={len(safe_ranges)}:v=1:a=1[outv][outa]"
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-filter_complex", fc,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        output_path,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.returncode == 0


def scan_and_censor_nsfw(
    video_path: str,
    censor_mode: str = "blur",
    max_nsfw_ratio: float = 0.65,
) -> dict:
    """
    End-to-end safety check + auto-censoring on a video clip (in-place update if censored).
    Returns:
      {
        "action": "clean" | "censored" | "rejected",
        "segments": list[dict],
        "reason": str,
        "video_path": str,
      }
    """
    scan = detect_nsfw_segments(video_path)
    if not scan["has_nsfw"]:
        return {
            "action": "clean",
            "segments": [],
            "reason": "No sexual/NSFW scenes detected",
            "video_path": video_path,
        }

    segments = scan["segments"]
    duration = max(1.0, scan["duration_sec"])
    nsfw_total = sum(max(0.0, s["end_sec"] - s["start_sec"]) for s in segments)
    nsfw_ratio = nsfw_total / duration

    reasons_str = ", ".join(f"{s['start_sec']:.1f}s-{s['end_sec']:.1f}s ({s['reason']})" for s in segments)
    print(f"[!] NSFW Censor detected unsafe segment(s): {reasons_str} ({nsfw_ratio*100:.0f}% of clip)")

    if scan["blocked_by_safety"] or censor_mode == "reject" or nsfw_ratio >= max_nsfw_ratio:
        return {
            "action": "rejected",
            "segments": segments,
            "reason": f"Rejected due to explicit/sexual content ({nsfw_ratio*100:.0f}%): {reasons_str}",
            "video_path": video_path,
        }

    # Render censored copy into a temp file, then atomically replace input_path
    fd, tmp_out = tempfile.mkstemp(suffix=".mp4", dir=os.path.dirname(os.path.abspath(video_path)))
    os.close(fd)

    try:
        if censor_mode == "cut":
            ok = apply_cut_censor(video_path, tmp_out, segments, duration)
            if not ok:
                # Fallback to blur if cutting fails (e.g. missing audio stream)
                ok = apply_blur_censor(video_path, tmp_out, segments)
        else:
            ok = apply_blur_censor(video_path, tmp_out, segments)

        if ok and os.path.exists(tmp_out) and os.path.getsize(tmp_out) > 10000:
            os.replace(tmp_out, video_path)
            print(f"[+] Auto-censored clip ({censor_mode} mode): {os.path.basename(video_path)}")
            return {
                "action": "censored",
                "segments": segments,
                "reason": f"Auto-censored ({censor_mode}): {reasons_str}",
                "video_path": video_path,
            }
        else:
            return {
                "action": "rejected",
                "segments": segments,
                "reason": f"NSFW detected and censoring failed -> rejected for safety: {reasons_str}",
                "video_path": video_path,
            }
    finally:
        if os.path.exists(tmp_out):
            try:
                os.remove(tmp_out)
            except OSError:
                pass


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m src.twitch_clipper.nsfw_censor <video.mp4> [blur|cut|reject]")
        sys.exit(1)
    mode = sys.argv[2] if len(sys.argv) > 2 else "blur"
    result = scan_and_censor_nsfw(sys.argv[1], censor_mode=mode)
    print(json.dumps(result, indent=2))
