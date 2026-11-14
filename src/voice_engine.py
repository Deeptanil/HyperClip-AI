"""
Voice Engine using edge-tts.
Generates natural fast-paced narration with millisecond word timestamps and styled ASS subtitles.
"""

import os
import asyncio
import edge_tts

DEFAULT_VOICE = "en-US-ChristopherNeural"  # Fast, energetic young adult male voice
RATE = "+15%"                              # +15% tempo for snappy TikTok/Shorts pacing

async def synthesize_speech_with_timestamps(text, output_audio_path, voice=DEFAULT_VOICE, rate=RATE):
    """
    Synthesizes speech and records word-level timestamp offsets.
    Returns: list of dicts [{"word": str, "start": float, "end": float}]
    """
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    word_timestamps = []

    with open(output_audio_path, "wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start_sec = chunk["offset"] / 10_000_000
                duration_sec = chunk["duration"] / 10_000_000
                word = chunk["text"]
                word_timestamps.append({
                    "word": word,
                    "start": start_sec,
                    "end": start_sec + duration_sec
                })
            elif chunk["type"] == "SentenceBoundary":
                start_sec = chunk["offset"] / 10_000_000
                duration_sec = chunk["duration"] / 10_000_000
                sentence_words = chunk["text"].strip().split()
                if sentence_words:
                    word_duration = duration_sec / len(sentence_words)
                    for i, w in enumerate(sentence_words):
                        word_timestamps.append({
                            "word": w,
                            "start": start_sec + (i * word_duration),
                            "end": start_sec + ((i + 1) * word_duration)
                        })

    return word_timestamps

def format_ass_time(seconds):
    """Formats seconds into ASS timestamp format: H:MM:SS.cs"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def generate_ass_subtitles(word_timestamps, output_ass_path, video_w=1080, video_h=1920):
    """
    Generates dynamic word-by-word viral highlighted subtitles in ASS format.
    Active word is bright yellow, surrounding words white with thick black outline.
    """
    phrases = []
    chunk_size = 3
    for i in range(0, len(word_timestamps), chunk_size):
        chunk = word_timestamps[i:i + chunk_size]
        if chunk:
            phrases.append(chunk)

    ass_content = f"""[Script Info]
Title: ChainsFR Viral Subtitles
ScriptType: v4.00+
PlayResX: {video_w}
PlayResY: {video_h}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Impact,82,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,2,0,1,10,2,2,80,80,420,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    for chunk in phrases:
        p_start = chunk[0]["start"]
        p_end = chunk[-1]["end"]

        for word_info in chunk:
            w_start = word_info["start"]
            w_end = word_info["end"]

            line_parts = []
            for w in chunk:
                w_clean = w["word"].upper()
                if w is word_info:
                    line_parts.append(r"{\c&H0022FFFF\fscx115\fscy115}" + w_clean + r"{\r}")
                else:
                    line_parts.append(r"{\c&H00FFFFFF}" + w_clean + r"{\r}")

            rendered_text = " ".join(line_parts)
            ass_line = f"Dialogue: 0,{format_ass_time(w_start)},{format_ass_time(w_end)},Default,,0,0,0,,{rendered_text}\n"
            ass_content += ass_line

    with open(output_ass_path, "w", encoding="utf-8") as f:
        f.write(ass_content)

async def process_scene_audio(scenes, temp_dir):
    """
    Synthesizes audio for all scenes and calculates exact scene timing.
    Returns: full_audio_path, full_ass_path, timed_scenes, total_duration
    """
    os.makedirs(temp_dir, exist_ok=True)
    all_words = []
    timed_scenes = []
    scene_audios = []

    current_timeline_offset = 0.0

    for idx, sc in enumerate(scenes):
        scene_audio = os.path.join(temp_dir, f"scene_{idx}.mp3")
        words = await synthesize_speech_with_timestamps(sc["text"], scene_audio)
        
        if words:
            scene_duration = words[-1]["end"] + 0.35
        else:
            scene_duration = 3.0

        for w in words:
            all_words.append({
                "word": w["word"],
                "start": w["start"] + current_timeline_offset,
                "end": w["end"] + current_timeline_offset
            })

        timed_scenes.append({
            **sc,
            "start_time": current_timeline_offset,
            "duration": scene_duration,
            "end_time": current_timeline_offset + scene_duration,
            "audio_file": scene_audio
        })

        scene_audios.append(scene_audio)
        current_timeline_offset += scene_duration

    # Concat all scene audio files into full audio
    full_audio = os.path.join(temp_dir, "full_narration.mp3")
    concat_list = os.path.join(temp_dir, "concat.txt")
    with open(concat_list, "w") as f:
        for sa in scene_audios:
            f.write(f"file '{os.path.basename(sa)}'\n")

    import subprocess
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list, "-c", "copy", full_audio]
    subprocess.run(cmd, cwd=temp_dir, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Generate ASS Subtitle
    ass_path = os.path.join(temp_dir, "subtitles.ass")
    generate_ass_subtitles(all_words, ass_path)

    return full_audio, ass_path, timed_scenes, current_timeline_offset
