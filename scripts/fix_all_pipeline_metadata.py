"""
Batch Metadata Fixer & Generator for stream_pipeline clips.
1. Creates complete .json files for all orphan .mp4 files with AI-generated title, caption, and hook.
2. Rewrites all generic, broken, or single-sentence template captions across all .json files in stream_pipeline.
Uses the Gemini fallback cascade:
  gemini-3.5-flash-lite -> gemini-3.1-flash-lite -> gemini-2.5-flash-lite -> gemini-3.8-flash -> gemini-3.6-flash
"""

import os
import sys
import glob
import json
import re
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

from src.twitch_clipper.text_censor import sanitize_text_for_reach
from src.twitch_clipper.hook_generator import DEFAULT_GEMINI_MODELS

MODELS = DEFAULT_GEMINI_MODELS

# Helper to infer streamer and game from filename
STREAMER_KEYWORDS = {
    "kaicenat": ("KaiCenat", "kaicenat", "Grand Theft Auto VI", "ig_1", True),
    "kai_cenat": ("KaiCenat", "kaicenat", "Grand Theft Auto VI", "ig_1", True),
    "clix": ("Clix", "clix", "Grand Theft Auto VI", "ig_2", True),
    "darkviperau": ("DarkViperAU", "darkviperau", "Grand Theft Auto VI", "ig_2", True),
    "jynxzi": ("Jynxzi", "jynxzi", "Rainbow Six Siege", "ig_1", True),
    "lacy": ("Lacy", "lacy", "Grand Theft Auto VI", "ig_2", True),
    "jasontheween": ("JasonTheWeen", "jasontheween", "Grand Theft Auto VI", "ig_1", True),
    "jason": ("JasonTheWeen", "jasontheween", "Grand Theft Auto VI", "ig_1", True),
    "cinna": ("Cinna", "cinna", "Grand Theft Auto VI", "ig_2", True),
    "deansocool": ("DeanSoCool", "deansocool", "Grand Theft Auto V", "ig_2", False),
    "caseoh": ("CaseOh", "caseoh_", "Gaming", "ig_1", True),
    "xqc": ("xQc", "xqc", "Grand Theft Auto VI", "ig_1", True),
}

def infer_streamer_and_game(filename: str):
    f_lower = filename.lower()
    for kw, (sname, uuname, gname, acc, yt) in STREAMER_KEYWORDS.items():
        if kw in f_lower:
            return sname, uuname, gname, acc, yt
    # Default to Kai Cenat / GTA 6 if unknown
    return "Streamer", "streamer", "Grand Theft Auto VI", "ig_1", True

def generate_ai_metadata(streamer: str, game: str, context: str) -> dict:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or not genai:
        return {}

    prompt = f"""
You are an expert viral gaming content creator for TikTok, YouTube Shorts, and Instagram Reels.
Craft an authentic, high-CTR title, hook, and storytelling caption for this gaming highlight clip.

Context:
- Streamer: {streamer}
- Game: {game}
- Clip description / situation: {context}

RULES:
1. Title: 4 to 7 words in ALL-CAPS with 1-2 relevant emojis. Must describe the exact funny, crazy, or climactic event (NEVER generic like '{streamer} ON {game}' or 'CRAZY MOMENT').
2. Hook: 3 to 6 words punchy on-screen text overlay with 1 emoji (e.g. 'BRO WENT FULL ECONOMIST 😭' or 'HE ACTUALLY SURVIVED 💀').
3. Caption: A compelling 2-sentence narrative caption explaining specifically what happened, why it was hilarious or shocking, and ending with an engaging question to viewers. Include 4 relevant viral hashtags (#GTA6 #{streamer} #GamingMoments, etc.).

Output strictly valid JSON with this schema:
{{
  "title": "4 to 7 words ALL-CAPS title with emojis",
  "hook": "3 to 6 words ALL-CAPS hook overlay with emoji",
  "caption": "2-sentence compelling story caption with hashtags"
}}
"""

    client = genai.Client(api_key=api_key)
    for model_name in MODELS:
        try:
            resp = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.4,
                    max_output_tokens=500,
                )
            )
            raw = (resp.text or "").strip()
            data = json.loads(raw)
            if data.get("title") and data.get("caption") and data.get("hook"):
                print(f"    [+] Model {model_name} succeeded.")
                return data
        except Exception as e:
            print(f"    [!] {model_name} failed: {e}")

    return {}

def is_caption_weak(caption: str, title: str) -> bool:
    if not caption or len(caption.strip()) < 80:
        return True
    c_lower = caption.lower()
    if "on just chatting" in c_lower:
        return True
    if caption.count(".") <= 1 and len(caption) < 120:
        return True
    # If caption is simply 1 line followed by hashtags
    parts = caption.split("#")
    if len(parts) > 1 and len(parts[0].strip()) < 65:
        return True
    return False

def main():
    pipeline_dir = "output/stream_pipeline"
    mp4_files = sorted(glob.glob(f"{pipeline_dir}/*.mp4"))
    print(f"[*] Scanning {len(mp4_files)} mp4 files in {pipeline_dir}...")

    fixed_count = 0

    for mp4_path in mp4_files:
        base_name = os.path.splitext(os.path.basename(mp4_path))[0]
        if ".tmp_" in base_name:
            continue

        json_path = os.path.join(pipeline_dir, f"{base_name}.json")
        has_json = os.path.exists(json_path)

        data = {}
        if has_json:
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}

        cur_title = data.get("title", "")
        cur_caption = data.get("caption", "")
        cur_hook = data.get("hook", "")
        streamer = data.get("streamer")
        game = data.get("game")

        if not streamer or not game:
            sname, uname, gname, acc, yt = infer_streamer_and_game(base_name)
            streamer = streamer or sname
            game = game or gname
        else:
            uname = data.get("username", streamer.lower())
            acc = data.get("assigned_ig", "ig_1")
            yt = data.get("post_to_yt", True)

        needs_fix = (
            not has_json
            or not cur_title
            or cur_title == base_name.replace("_", " ")
            or is_caption_weak(cur_caption, cur_title)
            or not cur_hook
        )

        if not needs_fix:
            continue

        print(f"\n[!] Upgrading metadata for: {base_name}")
        context = f"{cur_title or base_name.replace('_', ' ')}. Streamer: {streamer}. Game: {game}."
        ai_res = generate_ai_metadata(streamer, game, context)

        if not ai_res or not ai_res.get("title"):
            print("    [!] Could not generate AI metadata, skipping.")
            continue

        new_title = sanitize_text_for_reach(ai_res["title"])
        new_hook = sanitize_text_for_reach(ai_res["hook"])
        new_caption = sanitize_text_for_reach(ai_res["caption"])

        # Populate or update data dict
        data["streamer"] = streamer
        data["username"] = uname
        data["game"] = game
        data["title"] = new_title
        data["hook"] = new_hook
        data["caption"] = new_caption
        data["target_accounts"] = [acc] + (["youtube"] if yt else [])
        data["assigned_ig"] = acc
        data["post_to_yt"] = yt
        data["post_to_ig"] = True
        data["posted_to_instagram"] = False
        data["posted_to_youtube"] = False
        data["priority"] = 4
        data["discarded"] = False
        data["ai_retitled"] = True

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"    -> TITLE:   {new_title}")
        print(f"    -> HOOK:    {new_hook}")
        print(f"    -> CAPTION: {new_caption}")
        fixed_count += 1

    print(f"\n[+] Successfully fixed/generated metadata for {fixed_count} clips!")

if __name__ == "__main__":
    main()
