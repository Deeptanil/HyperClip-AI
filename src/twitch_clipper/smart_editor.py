"""
HyperClip AI - Smart Dead-Air & Silence Fast-Forward Engine.
Detects pauses, silences, and low-activity screen moments (e.g. streamer reading chat,
checking phone, or static menus) and fast-forwards them (2.5x - 4x) to maintain
high viewer retention and avoid swipe-away fatigue on TikTok/Reels/Shorts.
"""

import os
import re
import json
import subprocess
import cv2
import numpy as np


def get_video_duration(video_path: str) -> float:
    """Return video duration in seconds via ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(res.stdout.strip())
    except Exception:
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        cap.release()
        return float(frames / fps) if fps > 0 else 0.0


def check_segment_motion(video_path: str, start_sec: float, end_sec: float, facecam: dict | None = None) -> float:
    """
    Fast visual frame difference measurement across a pause segment.
    Samples a single frame pair around the midpoint of the pause.
    Returns average delta motion score (0.0 to 255.0).
    """
    if not os.path.exists(video_path) or end_sec <= start_sec:
        return 0.0

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

    mid_sec = (start_sec + end_sec) / 2.0
    f1_idx = max(0, min(total_frames - 2, int(mid_sec * fps)))
    f2_idx = min(total_frames - 1, f1_idx + max(1, int(fps * 0.25)))

    cap.set(cv2.CAP_PROP_POS_FRAMES, f1_idx)
    ok1, f1 = cap.read()
    cap.set(cv2.CAP_PROP_POS_FRAMES, f2_idx)
    ok2, f2 = cap.read()
    cap.release()

    if not ok1 or not ok2:
        return 0.0

    # Downsample frames for lightning-fast diff calculation
    h, w = f1.shape[:2]
    small_w = 320
    small_h = int(h * (320 / w))
    g1 = cv2.cvtColor(cv2.resize(f1, (small_w, small_h)), cv2.COLOR_BGR2GRAY)
    g2 = cv2.cvtColor(cv2.resize(f2, (small_w, small_h)), cv2.COLOR_BGR2GRAY)
    diff = cv2.absdiff(g1, g2)

    if facecam:
        scale_x = small_w / w
        scale_y = small_h / h
        cx = int(facecam.get("x", 0) * scale_x)
        cy = int(facecam.get("y", 0) * scale_y)
        cw = int(facecam.get("w", 0) * scale_x)
        ch = int(facecam.get("h", 0) * scale_y)
        if cw > 0 and ch > 0:
            cam_slice = diff[cy:cy + ch, cx:cx + cw]
            if cam_slice.size > 0:
                diff = cam_slice

    return float(np.mean(diff))


def get_stream_audio_levels(video_path: str) -> tuple[float, float]:
    """Return (mean_volume_db, max_volume_db) via ffmpeg volumedetect."""
    cmd = ["ffmpeg", "-hide_banner", "-i", video_path, "-af", "volumedetect", "-f", "null", "-"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        mean_vol = -24.0
        max_vol = -1.0
        for line in proc.stderr.splitlines():
            m_mean = re.search(r"mean_volume:\s*(-?[\d\.]+)\s*dB", line)
            if m_mean:
                mean_vol = float(m_mean.group(1))
            m_max = re.search(r"max_volume:\s*(-?[\d\.]+)\s*dB", line)
            if m_max:
                max_vol = float(m_max.group(1))
        return mean_vol, max_vol
    except Exception:
        return -24.0, -1.0


def extract_speech_pauses(video_path: str, min_pause_sec: float = 1.3) -> list[tuple[float, float]]:
    """
    Extracts speech pause intervals where the streamer stops speaking for >= min_pause_sec.
    Uses faster-whisper word timestamps on 16kHz PCM audio to detect dead-air even
    when loud background game audio / music is playing.
    """
    if not os.path.exists(video_path):
        return []

    try:
        from faster_whisper import WhisperModel
        import wave
    except ImportError:
        return []

    wav_path = os.path.splitext(video_path)[0] + "_smart_pause.wav"
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", video_path, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", wav_path],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        with wave.open(wav_path, "rb") as wf:
            raw_bytes = wf.readframes(wf.getnframes())
        audio_np = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0

        model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
        segments, _ = model.transcribe(audio_np, word_timestamps=True)

        words = []
        for s in segments:
            for w in (s.words or []):
                txt = (w.word or "").strip()
                if txt:
                    words.append((float(w.start), float(w.end)))

        if not words:
            return []

        pauses = []
        duration = get_video_duration(video_path)

        # Leading speech pause
        if words[0][0] >= min_pause_sec + 1.2:
            pauses.append((1.5, words[0][0]))

        # Inter-word speech pauses
        for i in range(len(words) - 1):
            gap = words[i + 1][0] - words[i][1]
            if gap >= min_pause_sec:
                pauses.append((words[i][1], words[i + 1][0]))

        # Trailing speech pause
        if duration - words[-1][1] >= min_pause_sec + 1.0:
            pauses.append((words[-1][1], max(words[-1][1], duration - 1.0)))

        return pauses
    except Exception as e:
        print(f"[!] extract_speech_pauses error: {e}")
        return []
    finally:
        if os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except Exception:
                pass


def detect_dead_air_segments(
    video_path: str,
    silence_threshold_db: float | None = None,
    min_pause_sec: float = 1.3,
    max_motion_threshold: float = 22.0,
    facecam: dict | None = None,
    use_whisper_pauses: bool = True
) -> list[tuple[float, float]]:
    """
    Detects dead air intervals where audio is quiet or streamer is not speaking
    and visual motion is below max_motion_threshold for >= min_pause_sec.
    Combines faster-whisper speech pauses and FFmpeg silencedetect.
    """
    if not os.path.exists(video_path):
        return []

    duration = get_video_duration(video_path)
    if duration < min_pause_sec:
        return []

    raw_segments = []

    # 1. Speech pause extraction via faster-whisper
    if use_whisper_pauses:
        speech_pauses = extract_speech_pauses(video_path, min_pause_sec=min_pause_sec)
        raw_segments.extend(speech_pauses)

    # 2. Audio silence detection via FFmpeg
    if silence_threshold_db is None or silence_threshold_db < -40.0:
        mean_vol, _ = get_stream_audio_levels(video_path)
        eff_thresh = round(min(-24.0, mean_vol - 1.5), 1)
    else:
        eff_thresh = float(silence_threshold_db)

    cmd = [
        "ffmpeg", "-hide_banner", "-nostats",
        "-i", video_path,
        "-af", f"silencedetect=noise={eff_thresh}dB:d={min_pause_sec}",
        "-f", "null", "-"
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        raw_log = proc.stderr or ""
        current_start = None
        for line in raw_log.splitlines():
            start_m = re.search(r"silence_start:\s*([\d\.]+)", line)
            if start_m:
                current_start = float(start_m.group(1))
            end_m = re.search(r"silence_end:\s*([\d\.]+)", line)
            if end_m and current_start is not None:
                end_val = float(end_m.group(1))
                if end_val - current_start >= min_pause_sec:
                    raw_segments.append((current_start, end_val))
                current_start = None
        if current_start is not None and (duration - current_start) >= min_pause_sec:
            raw_segments.append((current_start, duration))
    except Exception as e:
        print(f"[!] silencedetect execution failed: {e}")

    if not raw_segments:
        return []

    # Merge overlapping or close intervals (< 0.5s apart)
    merged = []
    for s_start, s_end in sorted(raw_segments, key=lambda x: x[0]):
        if not merged:
            merged.append([s_start, s_end])
        else:
            prev = merged[-1]
            if s_start <= prev[1] + 0.5:
                prev[1] = max(prev[1], s_end)
            else:
                merged.append([s_start, s_end])

    # Filter by visual motion guard:
    # If high action is occurring on screen despite low speech (e.g. intense boss battle), do NOT fast-forward!
    dead_air_segments = []
    for start, end in merged:
        # Don't fast-forward within the first 1.2s (intro hook) or last 1.0s (outro landing)
        adj_start = max(1.2, start)
        adj_end = min(duration - 1.0, end)
        if adj_end - adj_start < min_pause_sec:
            continue

        if max_motion_threshold > 0:
            motion = check_segment_motion(video_path, adj_start, adj_end, facecam=facecam)
            if motion > max_motion_threshold:
                # Active gameplay/screen motion; keep at 1x
                continue

        dead_air_segments.append((round(adj_start, 2), round(adj_end, 2)))

    return dead_air_segments


def fast_forward_dead_air(
    input_video_path: str,
    output_video_path: str,
    speed_multiplier: float = 3.0,
    silence_threshold_db: float | None = None,
    min_pause_sec: float = 1.3,
    max_motion_threshold: float = 18.0,
    show_badge: bool = True,
    facecam: dict | None = None
) -> tuple[str, list[dict]]:
    """
    Accelerates detected dead-air pauses by speed_multiplier (e.g. 3.0x).
    Returns (result_path, applied_segments_info).
    If no dead-air is detected, returns (input_video_path, []).
    """
    if not os.path.exists(input_video_path):
        return input_video_path, []

    duration = get_video_duration(input_video_path)
    if duration <= 0:
        return input_video_path, []

    dead_segments = detect_dead_air_segments(
        input_video_path,
        silence_threshold_db=silence_threshold_db,
        min_pause_sec=min_pause_sec,
        max_motion_threshold=max_motion_threshold,
        facecam=facecam
    )

    if not dead_segments:
        return input_video_path, []

    print(f"[*] Smart Editor: Detected {len(dead_segments)} dead-air intervals in {os.path.basename(input_video_path)}: {dead_segments}")

    # Build timeline slices [ (start, end, is_ff) ]
    slices = []
    cursor = 0.0

    for s_start, s_end in dead_segments:
        if s_start > cursor + 0.1:
            slices.append((cursor, s_start, False))
        slices.append((s_start, s_end, True))
        cursor = s_end

    if cursor < duration - 0.1:
        slices.append((cursor, duration, False))

    if not any(is_ff for _, _, is_ff in slices):
        return input_video_path, []

    # Build FFmpeg filter_complex graph
    v_filters = []
    a_filters = []
    concat_inputs = []

    # Compute atempo chain for arbitrary speed (atempo accepts 0.5 to 2.0 per filter)
    # E.g. speed 3.0 -> atempo=2.0,atempo=1.5
    speed = max(1.5, min(4.0, float(speed_multiplier)))
    if speed <= 2.0:
        atempo_str = f"atempo={speed:.2f}"
    else:
        atempo_str = f"atempo=2.0,atempo={speed / 2.0:.2f}"

    for i, (s_start, s_end, is_ff) in enumerate(slices):
        v_tag = f"v{i}"
        a_tag = f"a{i}"

        if not is_ff:
            # Normal 1x playback
            v_filters.append(f"[0:v]trim=start={s_start}:end={s_end},setpts=PTS-STARTPTS[{v_tag}]")
            a_filters.append(f"[0:a]atrim=start={s_start}:end={s_end},asetpts=PTS-STARTPTS[{a_tag}]")
        else:
            # Fast-forward playback (speed_multiplier x)
            ff_v = f"[0:v]trim=start={s_start}:end={s_end},setpts=(PTS-STARTPTS)/{speed:.2f}"
            if show_badge:
                ff_v += (
                    f",drawtext=text='>> FAST-FORWARD {speed:.0f}X':"
                    "fontcolor=yellow:fontsize=44:box=1:boxcolor=black@0.75:boxborderw=12:"
                    "x=(w-tw)/2:y=140"
                )
            ff_v += f"[{v_tag}]"
            v_filters.append(ff_v)

            # Duck volume during fast-forward so chipmunk breathing/noise doesn't overpower
            a_filters.append(
                f"[0:a]atrim=start={s_start}:end={s_end},asetpts=PTS-STARTPTS,{atempo_str},volume=0.45[{a_tag}]"
            )

        concat_inputs.append(f"[{v_tag}][{a_tag}]")

    concat_filter = f"{''.join(concat_inputs)}concat=n={len(slices)}:v=1:a=1[outv][outa]"
    full_filter_complex = ";".join(v_filters + a_filters + [concat_filter])

    os.makedirs(os.path.dirname(os.path.abspath(output_video_path)), exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-i", input_video_path,
        "-filter_complex", full_filter_complex,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        output_video_path
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"[!] Fast-forward FFmpeg error: {e.stderr[-600:] if e.stderr else str(e)}")
        return input_video_path, []

    if os.path.exists(output_video_path) and os.path.getsize(output_video_path) > 1000:
        new_dur = get_video_duration(output_video_path)
        saved_sec = duration - new_dur
        print(f"[+] Smart Editor successfully accelerated {len(dead_segments)} pauses! New duration: {new_dur:.1f}s (saved {saved_sec:.1f}s dead-air)")
        meta_list = [{"start": s, "end": e, "speed": speed} for s, e in dead_segments]
        return output_video_path, meta_list
    else:
        return input_video_path, []


def apply_audio_bleeping(video_path: str, output_path: str, bleep_segments: list[tuple[float, float]]) -> bool:
    """
    Applies 1000Hz sine beep gating to mute and bleep swear words in video_path.
    Uses -c:v copy to preserve video quality without re-encoding frames.
    """
    if not bleep_segments or not os.path.exists(video_path):
        return False

    duration = get_video_duration(video_path)
    conds = "+".join([f"between(t,{s:.3f},{e:.3f})" for s, e in bleep_segments])
    audio_filter = (
        f"[0:a]volume=enable='{conds}':volume=0[clean_a];"
        f"sine=frequency=1000:duration={duration + 5.0}[beep_raw];"
        f"[beep_raw]volume=enable='{conds}':volume=0.30,volume=enable='not({conds})':volume=0[beep_gated];"
        f"[clean_a][beep_gated]amix=inputs=2:duration=first:dropout_transition=0,loudnorm=I=-16:TP=-1.5:LRA=11[aout]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-filter_complex", audio_filter,
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        output_path
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            print(f"[+] Successfully bleeped {len(bleep_segments)} profanity audio segment(s) -> {os.path.basename(output_path)}")
            return True
        else:
            print(f"[!] Bleeping failed: {res.stderr[-400:] if res.stderr else 'unknown error'}")
            return False
    except Exception as e:
        print(f"[!] Bleeping exception: {e}")
        return False

