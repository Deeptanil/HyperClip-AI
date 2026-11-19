"""
Stickman Stop-Motion Viral Video Generator (ChainsFR Style).
Generates ready-to-post 1080x1920 vertical shorts with 0 cost and 0 paid APIs.
"""

import os
import sys
import asyncio
import argparse
import shutil

# Add src to python path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from script_generator import generate_script
from voice_engine import process_scene_audio
from sound_fx import ensure_sfx_library
from video_assembler import build_video

async def generate_single_video(topic=None, output_path="output_stickman.mp4", provider="template", api_key=None):
    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if not output_dir:
        output_path = os.path.join("output", output_path)
        os.makedirs("output", exist_ok=True)
    else:
        os.makedirs(output_dir, exist_ok=True)

    temp_dir = os.path.abspath("./temp_build")
    assets_dir = os.path.abspath("./assets/sfx")
    
    try:
        os.makedirs(temp_dir, exist_ok=True)
        
        # 1. Generate SFX library
        print("[1/4] Preparing sound effects library...")
        sfx_paths = ensure_sfx_library(assets_dir)
        
        # 2. Generate Story Script
        print("[2/4] Generating ChainsFR-style viral story script...")
        script = generate_script(topic=topic, api_key=api_key, provider=provider)
        print(f"      Title: \"{script.get('title', 'Stickman Story')}\"")
        print(f"      Scenes: {len(script['scenes'])}")
        
        # 3. Synthesize Speech & Word Timestamps
        print("[3/4] Synthesizing energetic narration & generating karaoke subtitles...")
        full_audio, ass_path, timed_scenes, duration = await process_scene_audio(script["scenes"], temp_dir)
        print(f"      Total audio duration: {duration:.2f}s")
        
        # 4. Render Stop-Motion Animation & Compile
        print("[4/4] Rendering stop-motion stickman frames and encoding video...")
        final_mp4 = build_video(timed_scenes, full_audio, ass_path, sfx_paths, output_path, temp_dir)
        print(f"\n[DONE] Video ready at: {os.path.abspath(final_mp4)}")
        return final_mp4
        
    finally:
        # Clean up temporary build files
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

def main():
    parser = argparse.ArgumentParser(description="ChainsFR-Style Automated Stickman Video Generator")
    parser.add_argument("--topic", type=str, default=None, help="Video topic or theme")
    parser.add_argument("--output", type=str, default="output_stickman.mp4", help="Output MP4 file path")
    parser.add_argument("--provider", type=str, choices=["template", "gemini"], default="template", help="Script generation provider")
    parser.add_argument("--api-key", type=str, default=os.getenv("GEMINI_API_KEY"), help="API Key for LLM script generation")
    parser.add_argument("--batch", type=int, default=1, help="Number of videos to generate")

    args = parser.parse_args()

    for i in range(args.batch):
        out_name = args.output
        if args.batch > 1:
            base, ext = os.path.splitext(args.output)
            out_name = f"{base}_{i+1}{ext}"
        print(f"\n=== Generating Video {i+1}/{args.batch} ===")
        asyncio.run(generate_single_video(
            topic=args.topic,
            output_path=out_name,
            provider=args.provider,
            api_key=args.api_key
        ))

def app(environ, start_response):
    """Vercel serverless compatibility handler."""
    start_response("200 OK", [("Content-Type", "text/plain")])
    return [b"HyperClip AI API Handler"]

application = app
handler = app

if __name__ == "__main__":
    main()
