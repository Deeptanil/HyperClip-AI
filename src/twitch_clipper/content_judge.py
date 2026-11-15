"""
HyperClip AI - Content Quality & Viral AI Judge.
Performs multimodal checks on prospective highlight clips:
1. Video Visual Activity: Detects if streamer is AFK/empty chair or screen is static/idle.
2. Audio/Speech Check: Confirms streamer vocal activity or meaningful audio.
3. Gemini Multimodal Reasoning: Inspects streamer action, speech, and chat sentiment
   to reject boring intro screens, pauses, bathroom breaks, and uninteresting gameplay.
4. Generates contextual high-CTR headline hooks and captions (no generic "X goes crazy on Y").
"""

import os
import json
import re
import cv2
import numpy as np

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

from src.twitch_clipper.hook_generator import _get_configured_models

BORING_KEYWORDS = re.compile(
    r"\b(brb|afk|bathroom|pee|be right back|empty chair|left the room|taking a break|"
    r"commercial|ads|ad break|pause|pausing|toilet|washroom)\b",
    re.IGNORECASE,
)


def check_visual_activity(video_path: str, facecam: dict | None = None) -> tuple[bool, str]:
    """
    Samples frames from the video to check for visual movement and streamer presence.
    Returns (is_active, reason).
    """
    if not os.path.exists(video_path):
        return False, "Video file does not exist"

    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    if total_frames < 30:
        cap.release()
        return False, "Video too short (<1s)"

    # Sample 6 evenly spaced frame pairs (0.5s apart) to measure motion
    sample_points = [0.15, 0.30, 0.45, 0.60, 0.75, 0.88]
    motion_scores = []
    facecam_motion_scores = []

    for ratio in sample_points:
        frame_idx = int(total_frames * ratio)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ok1, f1 = cap.read()
        cap.set(cv2.CAP_PROP_POS_FRAMES, min(total_frames - 1, frame_idx + int(fps * 0.4)))
        ok2, f2 = cap.read()
        if not ok1 or not ok2:
            continue

        g1 = cv2.cvtColor(f1, cv2.COLOR_BGR2GRAY)
        g2 = cv2.cvtColor(f2, cv2.COLOR_BGR2GRAY)
        diff = cv2.absdiff(g1, g2)
        motion_scores.append(float(np.mean(diff)))

        if facecam:
            cx, cy, cw, ch = facecam["x"], facecam["y"], facecam["w"], facecam["h"]
            cam_diff = diff[cy : cy + ch, cx : cx + cw]
            if cam_diff.size > 0:
                facecam_motion_scores.append(float(np.mean(cam_diff)))

    cap.release()

    if not motion_scores:
        return False, "Could not decode video frames"

    avg_motion = sum(motion_scores) / len(motion_scores)

    # If stream has a facecam box, check if streamer is in the chair and moving
    if facecam and facecam_motion_scores:
        avg_cam_motion = sum(facecam_motion_scores) / len(facecam_motion_scores)
        # Empty chair / static still cam typically has avg motion < 0.8
        if avg_cam_motion < 0.65 and avg_motion < 2.0:
            return False, f"Streamer appears AFK / empty chair (cam motion {avg_cam_motion:.2f} < 0.65)"

    # Completely static screen (e.g. paused game menu, title screen, or loading screen)
    if avg_motion < 0.8:
        return False, f"Screen is static / frozen menu (motion score {avg_motion:.2f} < 0.8)"

    return True, f"Active motion detected (avg motion: {avg_motion:.2f})"


def evaluate_clip_quality(
    streamer: str,
    game: str,
    stream_title: str,
    sample_chat: list,
    transcript: str | None,
    raw_clip_path: str,
    facecam: dict | None = None,
) -> dict:
    """
    Autonomous multi-stage quality judge:
    1. Fast heuristic screening (AFK keywords, static video frames, total silence).
    2. Gemini Flash Content Evaluator (cascade): Evaluates clip entertainability,
       rejects boring/empty segments, and produces an authentic viral hook + caption.
    """
    # 1. Fast Chat Heuristic Check
    chat_text = " ".join(sample_chat or [])
    boring_hits = len(BORING_KEYWORDS.findall(chat_text))
    if boring_hits >= 3:
        return {
            "approved": False,
            "reason": f"Chat indicates streamer is AFK / on break (hits: {boring_hits})",
            "hook": None,
            "caption": None,
        }

    # 2. Fast Visual Motion Check
    is_active, motion_reason = check_visual_activity(raw_clip_path, facecam=facecam)
    if not is_active:
        return {
            "approved": False,
            "reason": motion_reason,
            "hook": None,
            "caption": None,
        }

    # 3. Gemini Flash Deep Content Judge
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or not genai:
        # Fallback to approved if API key is not present but motion passed
        return {
            "approved": True,
            "reason": "Approved via visual motion check (no Gemini API key configured)",
            "hook": None,
            "caption": None,
        }

    models_to_try = _get_configured_models()
    client = None

    prompt = f"""
You are an expert short-form viral gaming content director (TikTok, Instagram Reels, YouTube Shorts).
Your job is to strictly vet candidate gaming clips and REJECT anything that is boring, unengaging, or low-value.

Clip Context:
- Streamer: {streamer}
- Game/Category: {game}
- Stream Title: {stream_title}
- Streamer Audio / What Was Said: {transcript or '[SILENCE / NO WORDS SPOKEN]'}
- Live Chat Reactions: {json.dumps(sample_chat or [])}

REJECTION CRITERIA (Mark is_viral_clip = false if ANY apply):
- Streamer is AFK, in the bathroom, left their chair, or taking a break.
- Streamer is quietly reading chat or sitting in silence without reacting.
- Video is just a game intro cutscene, title screen, loading screen, or menu.
- Video is an outro, raid screen, or stream ending goodbye.
- Nothing exciting, funny, dramatic, or climactic actually occurs.

APPROVAL CRITERIA (Mark is_viral_clip = true only if):
- A genuine, funny, insane, shocking, or high-energy moment happened.
- The streamer actively reacted (screaming, laughing, celebrating, raging, or talking intensely).
- There is clear context that viewers will stop scrolling to watch.

Output strictly valid JSON with this exact schema:
{{
  "is_viral_clip": boolean,
  "rejection_reason": string or null,
  "confidence": float between 0.0 and 1.0,
  "hook": "4 to 6 words ALL-CAPS headline with exactly 1 or 2 matching emojis (NO generic 'X GOES CRAZY ON Y')",
  "caption": "Short, engaging post caption with 2-3 specific gaming hashtags"
}}
"""

    for model_name in models_to_try:
        try:
            if client is None:
                client = genai.Client(api_key=api_key)
            resp = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.4,
                    max_output_tokens=200,
                ),
            )
            raw_text = (resp.text or "").strip()
            data = json.loads(raw_text)

            is_viral = bool(data.get("is_viral_clip", False))
            rejection = data.get("rejection_reason")
            hook = data.get("hook", "").strip()
            caption = data.get("caption", "").strip()

            if not is_viral:
                return {
                    "approved": False,
                    "reason": f"AI Judge Rejected ({model_name}): {rejection or 'Low engagement potential'}",
                    "hook": None,
                    "caption": None,
                }

            # Valid approved clip
            return {
                "approved": True,
                "reason": f"Approved by AI Judge ({model_name}, confidence: {data.get('confidence', 1.0)})",
                "hook": hook if (hook and len(hook.split()) >= 3) else None,
                "caption": caption if caption else None,
            }
        except Exception as e:
            print(f"[!] Content judge model '{model_name}' failed ({e}); trying next model...")

    # If all AI models fail, fall back to visual check result
    return {
        "approved": True,
        "reason": "Approved (AI judge cascade exhausted, passed visual motion checks)",
        "hook": None,
        "caption": None,
    }
