"""
Video Assembler: Renders all frames, mixes audio with timed SFX,
burns viral subtitles, and exports the final 1080x1920 MP4 via FFmpeg.
"""

import os
import shutil
import subprocess
from stickman_renderer import render_stickman_frame

FPS = 8  # 8 FPS authentic stop-motion frame rate

def build_video(timed_scenes, full_audio_path, ass_path, sfx_paths, output_mp4, temp_dir):
    """
    Renders frames and compiles everything into final vertical short.
    """
    frames_dir = os.path.join(temp_dir, "frames")
    os.makedirs(frames_dir, exist_ok=True)

    total_duration = timed_scenes[-1]["end_time"]
    total_frames = int(total_duration * FPS)

    print(f"[*] Rendering {total_frames} stop-motion frames ({total_duration:.1f}s @ {FPS} FPS)...")

    # Determine state per frame
    for f in range(total_frames):
        current_time = f / FPS

        # Find active scene
        active_scene = timed_scenes[-1]
        for sc in timed_scenes:
            if sc["start_time"] <= current_time < sc["end_time"]:
                active_scene = sc
                break

        # Check if SFX is actively bursting
        sfx_active = False
        time_into_scene = current_time - active_scene["start_time"]
        if active_scene.get("sfx") and time_into_scene < 0.25:
            sfx_active = True

        camera_mode = active_scene.get("camera", "normal")
        if sfx_active and camera_mode != "shake":
            # Add sudden shake on sfx hits
            if active_scene.get("sfx") == "boom":
                camera_mode = "shake"

        frame_img = render_stickman_frame(
            frame_idx=f,
            emotion=active_scene.get("emotion", "talking"),
            pose=active_scene.get("pose", "hands_up"),
            camera=camera_mode,
            is_sfx_active=sfx_active
        )

        frame_path = os.path.join(frames_dir, f"frame_{f:05d}.png")
        frame_img.save(frame_path)

    # Prepare SFX mixing with ffmpeg complex filter
    # Base narration audio is input 0
    inputs = ["-i", full_audio_path]
    filter_complex_parts = ["[0:a]volume=1.0[a0]"]
    mix_labels = ["[a0]"]

    input_idx = 1
    for sc in timed_scenes:
        sfx_name = sc.get("sfx")
        if sfx_name and sfx_name in sfx_paths:
            sfx_file = sfx_paths[sfx_name]
            delay_ms = int(sc["start_time"] * 1000)
            inputs.extend(["-i", sfx_file])
            filter_complex_parts.append(
                f"[{input_idx}:a]adelay={delay_ms}|{delay_ms},volume=0.85[a{input_idx}]"
            )
            mix_labels.append(f"[a{input_idx}]")
            input_idx += 1

    mix_str = "".join(mix_labels) + f"amix=inputs={input_idx}:duration=first:dropout_transition=2[aout]"
    full_filter = ";".join(filter_complex_parts) + ";" + mix_str

    mixed_audio_path = os.path.join(temp_dir, "mixed_audio.wav")
    cmd_audio = ["ffmpeg", "-y"] + inputs + ["-filter_complex", full_filter, "-map", "[aout]", mixed_audio_path]
    subprocess.run(cmd_audio, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Final Video Assembly: Frame sequence + Audio + Burned Subtitles
    print("[*] Assembling video with FFmpeg...")
    
    # Subtitle file path escaped for FFmpeg
    clean_ass_path = ass_path.replace("\\", "/").replace(":", "\\:")
    video_filter = f"ass='{clean_ass_path}'"

    cmd_video = [
        "ffmpeg", "-y",
        "-r", str(FPS),
        "-i", os.path.join(frames_dir, "frame_%05d.png"),
        "-i", mixed_audio_path,
        "-vf", video_filter,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        output_mp4
    ]

    subprocess.run(cmd_video, check=True)
    print(f"[+] Video rendered successfully: {output_mp4}")
    return output_mp4
