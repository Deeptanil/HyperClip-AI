"""
9:16 Portrait Video Reframer (Solid Black Background, Auto Facecam Stacking).
- If a corner facecam is detected: stacks Facecam (Top) + Gameplay (Bottom) on solid #000000 black.
- If no facecam is detected: centers Gameplay on solid #000000 black.
- Zero blurred backgrounds.
"""

import os
import json
import shutil
import subprocess
from dotenv import load_dotenv

load_dotenv()


def get_video_dimensions(video_path: str) -> tuple:
    """Returns (width, height, duration_sec) via ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height:format=duration",
        "-of", "json",
        video_path,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(res.stdout)
    stream = data["streams"][0]
    w = int(stream["width"])
    h = int(stream["height"])
    dur = float(data.get("format", {}).get("duration", 0))
    return w, h, dur


# Calibrated facecam crop profiles for top streamers (when streaming gameplay)
STREAMER_CAM_PROFILES = {
    "kaicenat": {"corner": "tl", "w_pct": 0.22, "h_pct": 0.28},
    "caseoh_": {"corner": "tl", "w_pct": 0.22, "h_pct": 0.28},
    "xqc": {"corner": "tl", "w_pct": 0.22, "h_pct": 0.28},
    "clix": {"corner": "br", "w_pct": 0.22, "h_pct": 0.28},
    "jynxzi": {"corner": "tr", "w_pct": 0.22, "h_pct": 0.28},
    "cinna": {"corner": "tl", "w_pct": 0.22, "h_pct": 0.28},
    "jasontheween": {"corner": "tl", "w_pct": 0.22, "h_pct": 0.28},
    "stableronaldo": {"corner": "tl", "w_pct": 0.22, "h_pct": 0.28},
}

# Categories where the full video is already a camera / person (IRL, Just Chatting)
# These MUST NEVER be dual-stacked.
FULL_CAMERA_CATEGORIES = {
    "just chatting",
    "irl",
    "pools, hot tubs, & beaches",
    "travel & outdoors",
    "talk shows & podcasts",
    "special events",
    "fitness & health",
    "art",
    "beauty & body art",
}


def compute_facecam_crop(box_2d: list, width: int, height: int, target_aspect: float = 1080.0 / 680.0) -> dict:
    """
    Expands a detected [ymin, xmin, ymax, xmax] box (0-1000 scale)
    to cleanly fit the top 1080x680 portrait slot without distortion.
    """
    ymin, xmin, ymax, xmax = box_2d
    bx = (xmin / 1000.0) * width
    by = (ymin / 1000.0) * height
    bw = ((xmax - xmin) / 1000.0) * width
    bh = ((ymax - ymin) / 1000.0) * height

    center_x = bx + bw / 2.0
    center_y = by + bh / 2.0

    # Expand to fit target aspect ratio with 12% breathing room
    padded_w = bw * 1.12
    padded_h = bh * 1.12

    if padded_w / max(1.0, padded_h) < target_aspect:
        padded_w = padded_h * target_aspect
    else:
        padded_h = padded_w / target_aspect

    crop_w = int(min(width, padded_w))
    crop_h = int(min(height, padded_h))
    crop_w -= crop_w % 2
    crop_h -= crop_h % 2

    crop_x = int(center_x - crop_w / 2.0)
    crop_y = int(center_y - crop_h / 2.0)
    crop_x = max(0, min(width - crop_w, crop_x))
    crop_y = max(0, min(height - crop_h, crop_y))
    crop_x -= crop_x % 2
    crop_y -= crop_y % 2

    return {"x": crop_x, "y": crop_y, "w": crop_w, "h": crop_h}


def _detect_facecam_ai(video_path: str, width: int, height: int) -> dict | None:
    """
    Uses Gemini AI Vision to dynamically detect the streamer's webcam box anywhere on the screen
    (floating, side margin, corners) or confirms pure gameplay with no camera.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        import cv2
        from google import genai
        from google.genai import types
    except ImportError:
        return None

    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 100)
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(total * 0.30))
    ok, frame = cap.read()
    cap.release()
    if not ok or frame is None:
        return None

    ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    if not ok:
        return None

    client = genai.Client(api_key=api_key)
    prompt = f"""Analyze this livestream broadcast frame (width {width}, height {height}).
Is there a streamer webcam / facecam overlay box?
Streamers place their camera overlay on the sides or in corners, but not always flush against the screen edge.
If there is a facecam overlay box, return JSON:
{{
  "has_facecam": true,
  "box_2d": [ymin, xmin, ymax, xmax],
  "description": "brief description of location"
}}
Coordinates must be scaled 0 to 1000.
If no facecam exists (e.g. pure full-screen gameplay without camera, or full-camera IRL), return:
{{"has_facecam": false}}
"""
    for m in ["gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-3.8-flash"]:
        try:
            resp = client.models.generate_content(
                model=m,
                contents=[types.Part.from_bytes(data=buf.tobytes(), mime_type="image/jpeg"), prompt],
                config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.1)
            )
            data = json.loads(resp.text)
            if not data.get("has_facecam"):
                return None
            box = data.get("box_2d", [])
            if len(box) == 4:
                crop = compute_facecam_crop(box, width, height)
                if 80 <= crop["w"] <= width * 0.75 and 80 <= crop["h"] <= height * 0.75:
                    print(f"[+] AI Vision detected facecam overlay: {crop} ({data.get('description', '')})")
                    return crop
        except Exception as e:
            continue
    return None


def detect_facecam_region(
    video_path: str,
    width: int,
    height: int,
    streamer: str = None,
    game: str = None,
) -> dict | None:
    """
    Samples frames and detects if a streamer facecam overlay exists.
    - If category is Just Chatting / IRL: returns None (forces clean centered framing).
    - Primary: AI Vision dynamically detects floating/side webcam overlays.
    - Fallback: Calibrated streamer profiles or spatial detection.
    Returns {x, y, w, h} in pixel coordinates, or None if no facecam found.
    """
    if game and str(game).strip().lower() in FULL_CAMERA_CATEGORIES:
        print(f"[*] Stream category '{game}' is full-camera / IRL. Dual-stack disabled -> Centered 9:16 layout.")
        return None

    # 1. Primary: AI Vision Detection (handles floating, side, and margin cams accurately)
    ai_crop = _detect_facecam_ai(video_path, width, height)
    if ai_crop is not None:
        return ai_crop

    # 2. Secondary: Fallback to calibrated profile if available
    s_key = (streamer or "").strip().lower()
    if s_key in STREAMER_CAM_PROFILES:
        prof = STREAMER_CAM_PROFILES[s_key]
        corner = prof["corner"]
        cam_w = int(width * prof["w_pct"])
        cam_h = int(height * prof["h_pct"])
        cam_w -= cam_w % 2
        cam_h -= cam_h % 2

        if corner == "tl":
            cam_x, cam_y = 0, 0
        elif corner == "tr":
            cam_x, cam_y = width - cam_w, 0
        elif corner == "bl":
            cam_x, cam_y = 0, height - cam_h
        else:
            cam_x, cam_y = width - cam_w, height - cam_h

        print(f"[+] Using calibrated fallback profile for '{streamer}' ({corner}): crop {cam_w}x{cam_h} at ({cam_x},{cam_y})")
        return {"x": cam_x, "y": cam_y, "w": cam_w, "h": cam_h, "corner": corner}
    try:
        import cv2
    except ImportError:
        print("[!] opencv-python-headless not installed; skipping auto facecam detection.")
        return None

    if not hasattr(cv2, "CascadeClassifier") or not hasattr(cv2, "data"):
        print("[!] cv2.CascadeClassifier unavailable in this OpenCV build; defaulting to centered gameplay.")
        return None

    cascade_path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
    face_cascade = cv2.CascadeClassifier(cascade_path)

    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if total_frames < 10:
        cap.release()
        return None

    sample_indices = [int(total_frames * r) for r in (0.15, 0.30, 0.45, 0.60, 0.75, 0.88)]
    corner_hits = {"tl": [], "tr": [], "bl": [], "br": []}

    for idx in sample_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if not ok:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.15, minNeighbors=5, minSize=(40, 40))

        for (fx, fy, fw, fh) in faces:
            # Ignore huge center faces (full-screen webcam / Just Chatting)
            if fw > width * 0.25:
                continue
            cx = fx + fw / 2.0
            cy = fy + fh / 2.0

            # Classify into corner overlay zones (outer 35% horizontally, outer 40% vertically)
            is_left = cx < width * 0.35
            is_right = cx > width * 0.65
            is_top = cy < height * 0.40
            is_bottom = cy > height * 0.60

            if is_left and is_top:
                corner_hits["tl"].append((cx, cy, fw, fh))
            elif is_right and is_top:
                corner_hits["tr"].append((cx, cy, fw, fh))
            elif is_left and is_bottom:
                corner_hits["bl"].append((cx, cy, fw, fh))
            elif is_right and is_bottom:
                corner_hits["br"].append((cx, cy, fw, fh))

    cap.release()

    # Pick the corner with >= 2 consistent detections
    best_corner = max(corner_hits.keys(), key=lambda k: len(corner_hits[k]))
    hits = corner_hits[best_corner]
    if len(hits) < 2:
        return None

    # Standard OBS corner webcam box (~21.5% width, ~28% height) anchored to that corner
    cam_w = int(width * 0.215)
    cam_h = int(height * 0.28)
    # Ensure even dimensions
    cam_w -= cam_w % 2
    cam_h -= cam_h % 2

    if best_corner == "tl":
        cam_x, cam_y = 0, 0
    elif best_corner == "tr":
        cam_x, cam_y = width - cam_w, 0
    elif best_corner == "bl":
        cam_x, cam_y = 0, height - cam_h
    else:  # br
        cam_x, cam_y = width - cam_w, height - cam_h

    print(f"[+] Facecam detected in corner '{best_corner}' ({len(hits)} hits): crop {cam_w}x{cam_h} at ({cam_x},{cam_y})")
    return {"x": cam_x, "y": cam_y, "w": cam_w, "h": cam_h, "corner": best_corner}


def frame_to_portrait(
    input_mp4: str,
    output_mp4: str,
    ass_subtitle_path: str = None,
    banner_png: str = None,
    layout: str = "auto_stacked",
    outro_mp4: str = "assets/outro_bleep.mp4",
    streamer: str = None,
    game: str = None,
) -> str:
    """
    Renders a 1080x1920 solid-black background portrait clip.
    - auto_stacked: detects facecam -> stacked cam (top) + gameplay (bottom); else centered gameplay.
    - centered: forces centered gameplay on black background.
    - banner_png: transparent PNG overlay placed in the top safe area (above facecam).
    - outro_mp4: appends retro NO SIGNAL glitch outro with censor bleep for the final 2 seconds.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_mp4)), exist_ok=True)
    w, h, _ = get_video_dimensions(input_mp4)

    facecam = None
    if layout == "auto_stacked":
        facecam = detect_facecam_region(input_mp4, w, h, streamer=streamer, game=game)

    # Escape subtitle path for FFmpeg libass filter
    sub_filter = ""
    if ass_subtitle_path and os.path.exists(ass_subtitle_path):
        escaped_ass = ass_subtitle_path.replace("\\", "/").replace(":", "\\:")
        sub_filter = f",ass='{escaped_ass}'"

    cmd = ["ffmpeg", "-y", "-i", input_mp4]
    has_banner = banner_png and os.path.exists(banner_png)
    if has_banner:
        cmd.extend(["-i", banner_png])

    if facecam:
        # Top: Facecam scaled to 1080x680 placed at y=240
        # Bottom: Gameplay scaled to 1080x608 placed at y=930 via pad (preserves exact FPS & duration)
        # Canvas: 1080x1920 solid black (#000000)
        cx, cy, cw, ch = facecam["x"], facecam["y"], facecam["w"], facecam["h"]
        if has_banner:
            filter_complex = (
                f"[0:v]split=2[vcam][vgame];"
                f"[vcam]crop={cw}:{ch}:{cx}:{cy},scale=1080:680:force_original_aspect_ratio=increase,crop=1080:680[cam];"
                f"[vgame]scale=1080:608:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:930:black[canvas];"
                f"[canvas][cam]overlay=(W-w)/2:240:shortest=1[with_cam];"
                f"[with_cam][1:v]overlay=(W-w)/2:20{sub_filter}[vout]"
            )
        else:
            filter_complex = (
                f"[0:v]split=2[vcam][vgame];"
                f"[vcam]crop={cw}:{ch}:{cx}:{cy},scale=1080:680:force_original_aspect_ratio=increase,crop=1080:680[cam];"
                f"[vgame]scale=1080:608:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:930:black[canvas];"
                f"[canvas][cam]overlay=(W-w)/2:240:shortest=1{sub_filter}[vout]"
            )
    else:
        # No facecam -> Clean centered 16:9 gameplay on solid black background (starts at y=656)
        # Place banner_png at y=490 so the headline sits directly above the clip
        if has_banner:
            filter_complex = (
                f"[0:v]scale=1080:608:force_original_aspect_ratio=decrease,"
                f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black[canvas];"
                f"[canvas][1:v]overlay=(W-w)/2:490{sub_filter}[vout]"
            )
        else:
            filter_complex = (
                f"[0:v]scale=1080:608:force_original_aspect_ratio=decrease,"
                f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black{sub_filter}[vout]"
            )

    temp_framed = output_mp4 + ".tmp_framed.mp4"
    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", "0:a?",
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "22",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        temp_framed,
    ])

    print(f"[*] Framing 9:16 portrait ({'stacked facecam + gameplay' if facecam else 'centered gameplay'} on black)...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        if os.path.exists(temp_framed):
            try:
                os.remove(temp_framed)
            except Exception:
                pass
        raise RuntimeError(f"FFmpeg portrait framing failed: {res.stderr}")

    # Seamlessly append 2s retro glitch outro if asset is available
    if outro_mp4 and os.path.exists(outro_mp4):
        print(f"[*] Appending 2s retro glitch outro ({outro_mp4})...")
        concat_cmd = [
            "ffmpeg", "-y",
            "-i", temp_framed,
            "-i", outro_mp4,
            "-filter_complex",
            "[0:v]fps=30,scale=1080:1920,setsar=1[v0];"
            "[0:a]aformat=sample_rates=44100:channel_layouts=stereo[a0];"
            "[1:v]fps=30,scale=1080:1920,setsar=1[v1];"
            "[1:a]aformat=sample_rates=44100:channel_layouts=stereo[a1];"
            "[v0][a0][v1][a1]concat=n=2:v=1:a=1[vout][aout]",
            "-map", "[vout]",
            "-map", "[aout]",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            output_mp4,
        ]
        concat_res = subprocess.run(concat_cmd, capture_output=True, text=True)
        if os.path.exists(temp_framed):
            try:
                os.remove(temp_framed)
            except Exception:
                pass
        if concat_res.returncode != 0:
            print(f"[!] Warning: Outro concat failed, using framed video without outro: {concat_res.stderr}")
            shutil.move(temp_framed, output_mp4)
    else:
        shutil.move(temp_framed, output_mp4)

    return output_mp4
