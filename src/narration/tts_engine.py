"""
Narration Engine.
Supports:
1. Edge-TTS (Fast, high-fidelity, zero-setup, accurate word timestamps)
2. Kokoro-TTS (Open-weight 82M model with human breathing cadence)
"""

import os
import asyncio
import edge_tts

DEFAULT_VOICE = "en-US-ChristopherNeural"
NARRATION_RATE = "+10%"

async def generate_speech_edge(text, output_audio_path, voice=DEFAULT_VOICE, rate=NARRATION_RATE):
    """Generates audio via edge-tts with word-level timestamps."""
    comm = edge_tts.Communicate(text, voice, rate=rate)
    word_timestamps = []

    with open(output_audio_path, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start_sec = chunk["offset"] / 10_000_000
                duration_sec = chunk["duration"] / 10_000_000
                word_timestamps.append({
                    "word": chunk["text"],
                    "start": start_sec,
                    "end": start_sec + duration_sec
                })
            elif chunk["type"] == "SentenceBoundary":
                start_sec = chunk["offset"] / 10_000_000
                duration_sec = chunk["duration"] / 10_000_000
                sentence_words = chunk["text"].strip().split()
                if sentence_words:
                    w_dur = duration_sec / len(sentence_words)
                    for i, w in enumerate(sentence_words):
                        word_timestamps.append({
                            "word": w,
                            "start": start_sec + (i * w_dur),
                            "end": start_sec + ((i + 1) * w_dur)
                        })

    return word_timestamps

def format_ass_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def generate_subtitles_ass(word_timestamps, output_ass_path, video_w=1080, video_h=1920):
    """Generates punchy 3-word chunk karaoke subtitles styled in bold Impact."""
    phrases = []
    chunk_size = 3
    for i in range(0, len(word_timestamps), chunk_size):
        chunk = word_timestamps[i:i + chunk_size]
        if chunk:
            phrases.append(chunk)

    ass_content = f"""[Script Info]
Title: Storytelling Viral Subtitles
ScriptType: v4.00+
PlayResX: {video_w}
PlayResY: {video_h}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Impact,80,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,2,0,1,10,2,2,80,80,440,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    for chunk in phrases:
        for word_info in chunk:
            w_start = word_info["start"]
            w_end = word_info["end"]

            line_parts = []
            for w in chunk:
                w_clean = w["word"].upper()
                if w is word_info:
                    line_parts.append(r"{\c&H0000E6FF\fscx112\fscy112}" + w_clean + r"{\r}")
                else:
                    line_parts.append(r"{\c&H00FFFFFF}" + w_clean + r"{\r}")

            rendered_text = " ".join(line_parts)
            ass_line = f"Dialogue: 0,{format_ass_time(w_start)},{format_ass_time(w_end)},Default,,0,0,0,,{rendered_text}\n"
            ass_content += ass_line

    with open(output_ass_path, "w", encoding="utf-8") as f:
        f.write(ass_content)

async def synthesize_story_narration(scenes, temp_dir):
    """Synthesizes speech across all scenes, returns timed scene metadata."""
    os.makedirs(temp_dir, exist_ok=True)
    all_words = []
    timed_scenes = []
    scene_audios = []
    current_offset = 0.0

    for idx, sc in enumerate(scenes):
        scene_audio = os.path.join(temp_dir, f"scene_{idx}.mp3")
        words = await generate_speech_edge(sc["text"], scene_audio)

        duration = words[-1]["end"] + 0.3 if words else 3.5

        for w in words:
            all_words.append({
                "word": w["word"],
                "start": w["start"] + current_offset,
                "end": w["end"] + current_offset
            })

        timed_scenes.append({
            **sc,
            "start_time": current_offset,
            "duration": duration,
            "end_time": current_offset + duration,
            "audio_file": scene_audio
        })

        scene_audios.append(scene_audio)
        current_offset += duration

    # Concatenate into full audio
    full_audio = os.path.join(temp_dir, "full_narration.mp3")
    concat_txt = os.path.join(temp_dir, "concat.txt")
    with open(concat_txt, "w") as f:
        for sa in scene_audios:
            f.write(f"file '{os.path.basename(sa)}'\n")

    import subprocess
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_txt, "-c", "copy", full_audio]
    subprocess.run(cmd, cwd=temp_dir, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Subtitles
    ass_path = os.path.join(temp_dir, "subtitles.ass")
    generate_subtitles_ass(all_words, ass_path)

    return full_audio, ass_path, timed_scenes, current_offset
