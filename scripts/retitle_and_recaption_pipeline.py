"""
Batch AI Retitler and Recaptioner.
Iterates over clips in output/stream_pipeline/ and upgrades bad, generic, or duplicated
metadata with high-CTR, narrative-driven titles and informative captions using Gemini.
Cascade order:
  1. Gemini 3.5 Flash Lite
  2. Gemini 3.1 Flash Lite
  3. Gemini 2.5 Flash Lite
  4. Gemini 3.8 Flash
  5. Gemini 3.6 Flash
  6. Gemini 2.5 Flash
  7. Gemini 4 Hydrogen
"""

import os
import sys
import glob
import json
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

def generate_ai_metadata(streamer: str, game: str, cur_title: str, cur_caption: str, sample_chat: list) -> dict:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or not genai:
        return {}

    prompt = f"""
You are an expert viral gaming content creator for TikTok, YouTube Shorts, and Instagram Reels.
Fix the title and caption for this gaming highlight clip.

Current Metadata:
- Streamer: {streamer}
- Game: {game}
- Current Title: {cur_title}
- Current Caption: {cur_caption}
- Chat Reactions: {json.dumps(sample_chat or [])}

RULES:
1. Title: 4 to 7 words in ALL-CAPS with 1-2 emojis. Must describe the specific dramatic, funny, or climactic moment (NEVER generic like '{streamer} ON {game}' or 'CRAZY MOMENT').
2. Caption: A compelling 2-sentence story caption explaining the specific situation, why it went wrong or viral, and asking a viewer question. Includes 3-4 specific hashtags. NEVER say '{streamer} on {game}'.

Output strictly valid JSON with this schema:
{{
  "title": "4 to 7 words ALL-CAPS title with emojis",
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
            if data.get("title") and data.get("caption"):
                print(f"  [+] Success via {model_name}")
                return data
        except Exception as e:
            print(f"  [!] {model_name} failed: {e}")

    return {}

def main():
    json_files = sorted(glob.glob("output/stream_pipeline/*.json"))
    print(f"Found {len(json_files)} clips in output/stream_pipeline/")
    updated_count = 0

    for jf in json_files:
        with open(jf, "r", encoding="utf-8") as f:
            data = json.load(f)

        cur_title = data.get("title") or ""
        cur_caption = data.get("caption") or ""
        streamer = data.get("streamer") or "Streamer"
        game = data.get("game") or "Gaming"
        chat = data.get("sample_chat") or []

        # Check if caption is generic/template
        is_generic = (
            f"{streamer} on {game}!" in cur_caption
            or f"on {game}!" in cur_caption
            or cur_title == cur_caption.split("\n")[0] and len(cur_caption.split("\n")) <= 3
            or "on just chatting!" in cur_caption.lower()
        )

        if not is_generic:
            print(f"[SKIP] {os.path.basename(jf)} already has custom caption.")
            continue

        print(f"[*] Upgrading: {os.path.basename(jf)}")
        ai_res = generate_ai_metadata(streamer, game, cur_title, cur_caption, chat)
        if ai_res.get("title") and ai_res.get("caption"):
            new_title = sanitize_text_for_reach(ai_res["title"])
            new_caption = sanitize_text_for_reach(ai_res["caption"])

            data["title"] = new_title
            data["caption"] = new_caption
            data["ai_retitled"] = True

            with open(jf, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"    -> NEW TITLE: {new_title}")
            print(f"    -> NEW CAPTION: {new_caption[:80]}...")
            updated_count += 1

    print(f"\n[+] Finished upgrading {updated_count} clips in pipeline!")

if __name__ == "__main__":
    main()
