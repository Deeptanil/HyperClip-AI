"""
Free Local Word-by-Word Karaoke Captioner for Twitch Clips.
Uses faster-whisper (CPU INT8) to transcribe streamer audio and generate
bold ASS karaoke subtitles placed cleanly in the lower black safe margin.
"""

import os
import subprocess


def _format_ass_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def generate_clip_captions(video_path: str, ass_output_path: str, model_size: str = "tiny.en") -> str | None:
    """
    Transcribes speech from video_path using faster-whisper and writes an ASS subtitle file.
    Returns ass_output_path on success, or None if no speech / missing dependency.
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("[!] faster-whisper not installed; skipping clip captions.")
        return None

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
        return None

    try:
        import wave
        import numpy as np

        with wave.open(wav_path, "rb") as wf:
            raw_bytes = wf.readframes(wf.getnframes())
        audio_np = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0

        print(f"[*] Transcribing clip audio with faster-whisper ({model_size})...")
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        segments, _ = model.transcribe(audio_np, word_timestamps=True, vad_filter=True)

        words = []
        for seg in segments:
            if not seg.words:
                continue
            for w in seg.words:
                txt = (w.word or "").strip()
                if txt:
                    words.append({
                        "word": txt,
                        "start": float(w.start),
                        "end": float(w.end),
                    })
    except Exception as e:
        print(f"[!] Whisper transcription failed: {e}")
        return None
    finally:
        if os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except Exception:
                pass

    if not words:
        print("[-] No speech detected in clip; skipping subtitles.")
        return None

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
                clean = w["word"].upper().replace("{", "").replace("}", "")
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

    print(f"[+] Generated {len(words)} word-synced captions -> {ass_output_path}")
    return ass_output_path
