"""
Free Local Word-by-Word Karaoke Captioner for Twitch Clips with Auto-Profanity Censor & Bleeping.
Uses faster-whisper (CPU INT8) to transcribe streamer audio, detects swear words,
censors subtitle text (e.g. F**K, SH*T, B***H), and returns precise timestamps
for 1000Hz audio bleep generation in FFmpeg.
"""

import os
import re
import subprocess

# Root stems for swear / profanity words to censor and bleep
PROFANITY_ROOTS = [
    r"fuck", r"fck", r"fuk", r"shit", r"bitch", r"asshole", r"dumbass", r"jackass",
    r"dick", r"pussy", r"cunt", r"cock", r"nigg", r"fag", r"retard", r"whore", r"slut",
    r"bastard", r"motherfuck", r"bullshit", r"dipshit"
]
PROFANITY_REGEX = re.compile(r"^(" + "|".join(PROFANITY_ROOTS) + r")[a-z]*$", re.IGNORECASE)


def is_profane(text: str) -> bool:
    """Checks if a single word or token is profanity."""
    clean = re.sub(r"^[^\w]+|[^\w]+$", "", text)
    return bool(PROFANITY_REGEX.match(clean))


def censor_word(word: str) -> str:
    """Replaces inner characters with asterisks (e.g. FUCK -> F**K, BITCH -> B***H)."""
    m = re.match(r"^([^a-zA-Z]*)([a-zA-Z]+)([^a-zA-Z]*)$", word)
    if not m:
        return word
    prefix, core, suffix = m.groups()
    if is_profane(core):
        if len(core) <= 2:
            censored = "*" * len(core)
        elif len(core) == 3:
            censored = core[0] + "*" + core[-1]
        else:
            censored = core[0] + "*" * (len(core) - 2) + core[-1]
        return f"{prefix}{censored}{suffix}"
    return word


def merge_intervals(intervals: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Merges overlapping or touching (start, end) time intervals."""
    if not intervals:
        return []
    sorted_int = sorted(intervals, key=lambda x: x[0])
    merged = [sorted_int[0]]
    for cur in sorted_int[1:]:
        prev_s, prev_e = merged[-1]
        if cur[0] <= prev_e + 0.05:  # within 50ms merges into continuous bleep
            merged[-1] = (prev_s, max(prev_e, cur[1]))
        else:
            merged.append(cur)
    return merged


def _format_ass_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def generate_clip_captions(
    video_path: str,
    ass_output_path: str,
    model_size: str = "tiny.en",
    censor_profanity: bool = True
) -> tuple[str | None, list[tuple[float, float]]]:
    """
    Transcribes speech from video_path using faster-whisper and writes an ASS subtitle file.
    Censors swear words in subtitles and detects exact (start, end) timestamps for audio bleeping.
    Returns:
      (ass_output_path, bleep_segments) on success, or (None, []) on failure/no speech.
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("[!] faster-whisper not installed; skipping clip captions.")
        return None, []

    wav_path = os.path.splitext(video_path)[0] + "_16k.wav"
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", video_path, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", wav_path],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        print(f"[!] Audio extraction failed for captions: {e}")
        return None, []

    words = []
    bleep_intervals = []
    try:
        import wave
        import numpy as np

        with wave.open(wav_path, "rb") as wf:
            raw_bytes = wf.readframes(wf.getnframes())
        audio_np = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0

        print(f"[*] Transcribing clip audio with faster-whisper ({model_size})...")
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        segments, _ = model.transcribe(audio_np, word_timestamps=True, vad_filter=True)

        for seg in segments:
            if not seg.words:
                continue
            for w in seg.words:
                txt = (w.word or "").strip()
                if txt:
                    bad = is_profane(txt)
                    start_t = float(w.start)
                    end_t = float(w.end)
                    if bad:
                        # 60ms acoustic padding before and after to completely mute the expletive
                        b_start = max(0.0, start_t - 0.06)
                        b_end = end_t + 0.06
                        bleep_intervals.append((round(b_start, 3), round(b_end, 3)))
                    words.append({
                        "word": txt,
                        "start": start_t,
                        "end": end_t,
                        "is_profane": bad,
                    })
    except Exception as e:
        print(f"[!] Whisper transcription failed: {e}")
        return None, []
    finally:
        if os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except Exception:
                pass

    if not words:
        print("[-] No speech detected in clip; skipping subtitles.")
        return None, []

    bleep_segments = merge_intervals(bleep_intervals)
    if bleep_segments:
        print(f"[!] Detected {len(bleep_segments)} profanity audio segment(s) to bleep: {bleep_segments}")

    # Build ASS header (Bold Impact/Arial, positioned at y ~1640 in black bar below gameplay)
    ass_header = """[Script Info]
Title: HyperClip AI Subtitles
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Liberation Sans,72,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,6,2,2,60,60,260,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [ass_header]

    # Chunk into 3-word karaoke phrases
    chunk_size = 3
    for i in range(0, len(words), chunk_size):
        chunk = words[i : i + chunk_size]
        for active_idx, active_w in enumerate(chunk):
            t_start = active_w["start"]
            t_end = active_w["end"]
            if active_idx < len(chunk) - 1:
                t_end = min(t_end, chunk[active_idx + 1]["start"])
            if t_end <= t_start:
                t_end = t_start + 0.08

            styled_parts = []
            for j, w in enumerate(chunk):
                raw_w = w["word"]
                if censor_profanity and w.get("is_profane"):
                    display_w = censor_word(raw_w)
                else:
                    display_w = raw_w
                clean = display_w.upper().replace("{", "").replace("}", "")
                if j == active_idx:
                    # Highlighted active word in bright yellow (&H0000FFFF in BGR)
                    styled_parts.append(r"{\c&H0000FFFF&}" + clean + r"{\c&H00FFFFFF&}")
                else:
                    styled_parts.append(clean)

            text = " ".join(styled_parts)
            lines.append(f"Dialogue: 0,{_format_ass_time(t_start)},{_format_ass_time(t_end)},Default,,0,0,0,,{text}")

    os.makedirs(os.path.dirname(os.path.abspath(ass_output_path)), exist_ok=True)
    with open(ass_output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"[+] Generated {len(words)} word-synced captions (censored={censor_profanity}) -> {ass_output_path}")
    return ass_output_path, bleep_segments
