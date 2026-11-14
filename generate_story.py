"""
Autonomous Storytelling Studio CLI.
Generates 60-120s high-retention stick-figure animations across:
- Real-life & historical incidents
- Myths & folklore
- Humorous true tales
"""

import os
import sys
import asyncio
import argparse
import shutil
from dotenv import load_dotenv

load_dotenv()

# Add project root to sys.path
sys.path.append(os.path.dirname(__file__))

from src.story_engine.writer import generate_story_script
from src.narration.tts_engine import synthesize_story_narration
from src.sound_fx import ensure_sfx_library
from src.renderer.engine import render_story_video

async def build_story_video(category="history", topic=None, output_path="story_output.mp4", publish=False):
    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if not output_dir:
        output_path = os.path.join("output", output_path)
        os.makedirs("output", exist_ok=True)
    else:
        os.makedirs(output_dir, exist_ok=True)

    temp_dir = os.path.abspath("./temp_story_build")
    assets_dir = os.path.abspath("./assets/sfx")

    try:
        os.makedirs(temp_dir, exist_ok=True)

        print("\n" + "=" * 60)
        print("🎬 STARTING AUTONOMOUS STORYTELLING ENGINE")
        print("=" * 60)

        # 1. SFX Library
        print("[1/4] Checking sound effects library...")
        sfx_paths = ensure_sfx_library(assets_dir)

        # 2. Multi-Stage Scriptwriting & Editorial Gatekeeper
        print(f"[2/4] Generating & reviewing script (Category: {category})...")
        script = generate_story_script(category=category, topic=topic)
        print(f"      Title: \"{script.get('title')}\"")
        print(f"      Scenes: {len(script.get('scenes', []))} beats")

        # 3. Speech Synthesis & Timestamps
        print("[3/4] Synthesizing human narration & generating karaoke subtitles...")
        full_audio, ass_path, timed_scenes, total_duration = await synthesize_story_narration(script["scenes"], temp_dir)
        print(f"      Narration duration: {total_duration:.1f} seconds")

        # 4. Animation Compositing & Video Assembly
        print("[4/4] Rendering 9:16 multi-character animation with environments & props...")
        final_mp4 = render_story_video(timed_scenes, full_audio, ass_path, sfx_paths, output_path, temp_dir)

        print("\n" + "=" * 60)
        print(f"✅ VIDEO READY: {os.path.abspath(final_mp4)}")
        print(f"⏱  DURATION:    {total_duration:.1f}s")
        print("=" * 60)

        # Optional Auto-Publishing to YouTube Shorts
        if publish:
            print("[*] Initiating YouTube Shorts upload...")
            from src.uploaders.youtube_uploader import upload_short
            yt_url = upload_short(
                final_mp4,
                title=script.get("title", "Historical Story"),
                description=f"{script.get('title')}\n\n#Shorts #history #animation #storytime #mythology"
            )
            print(f"[+] Published live to YouTube: {yt_url}")

        return final_mp4

    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

def main():
    parser = argparse.ArgumentParser(description="Autonomous Storytelling Video Generation Platform")
    parser.add_argument("--category", choices=["history", "mythology", "humor"], default="history")
    parser.add_argument("--topic", type=str, default=None)
    parser.add_argument("--output", type=str, default="story_output.mp4")
    parser.add_argument("--publish", action="store_true", help="Auto-publish to YouTube Shorts after rendering")

    args = parser.parse_args()
    asyncio.run(build_story_video(
        category=args.category,
        topic=args.topic,
        output_path=args.output,
        publish=args.publish
    ))

if __name__ == "__main__":
    main()
