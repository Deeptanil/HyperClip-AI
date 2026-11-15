"""
9:16 Portrait Video Reframer (Solid Black Background, Auto Facecam Stacking).
- If a corner facecam is detected: stacks Facecam (Top) + Gameplay (Bottom) on solid #000000 black.
- If no facecam is detected: centers Gameplay on solid #000000 black.
- Zero blurred backgrounds.
"""

import os
import json
import subprocess


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


def detect_facecam_region(video_path: str, width: int, height: int) -> dict | None:
    """
    Samples frames and detects if a streamer facecam overlay exists in a corner.
    Returns {x, y, w, h, corner} in pixel coordinates, or None if no corner cam found.
    """
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
) -> str:
    """
    Renders a 1080x1920 solid-black background portrait clip.
    - auto_stacked: detects facecam -> stacked cam (top) + gameplay (bottom); else centered gameplay.
    - centered: forces centered gameplay on black background.
    - banner_png: transparent PNG overlay placed in the top safe area (above facecam).
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_mp4)), exist_ok=True)
    w, h, _ = get_video_dimensions(input_mp4)

    facecam = None
    if layout == "auto_stacked":
        facecam = detect_facecam_region(input_mp4, w, h)

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
        output_mp4,
    ])

    print(f"[*] Framing 9:16 portrait ({'stacked facecam + gameplay' if facecam else 'centered gameplay'} on black)...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg portrait framing failed: {res.stderr}")

    return output_mp4
