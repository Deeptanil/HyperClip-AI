"""
HyperClip AI - Viral Hook & Banner Generator.
1. Generates high-CTR 4-7 word headline hooks with relevant emojis using Gemini API (or intelligent rule-based fallback).
2. Renders crisp RGBA banner PNGs using Pilmoji for 100% full-color emoji rendering (no missing boxes or font glyph errors).
3. Produces safe filename slugs based on the generated hook.
"""

import os
import re
from PIL import Image, ImageFont
from pilmoji import Pilmoji

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

EMOJI_KEYWORDS = {
    "laugh": "😂",
    "dead": "💀",
    "crazy": "🤯",
    "insane": "🔥",
    "rocket": "🚀",
    "space": "🚀",
    "police": "🚨",
    "car": "🏎️",
    "rage": "🤬",
    "panic": "😱",
    "win": "🏆",
    "gta": "🔫",
    "money": "💰",
}


DEFAULT_GEMINI_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-3.6-flash",
    "gemini-3.8-flash",
]


def _get_configured_models() -> list:
    """Reads GEMINI_MODELS from environment, config.json, or default cascade."""
    env_models = os.getenv("GEMINI_MODELS")
    if env_models:
        return [m.strip() for m in env_models.split(",") if m.strip()]
    try:
        import json
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.json")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                custom = cfg.get("gemini_models")
                if custom and isinstance(custom, list):
                    return custom
    except Exception:
        pass
    return DEFAULT_GEMINI_MODELS


def slugify_hook(text: str) -> str:
    """Converts a hook headline into a clean filesystem slug."""
    clean = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "_", clean)[:36]


def generate_hook_text(streamer: str, game: str, stream_title: str, sample_chat: list = None, transcript: str = None) -> str:
    """
    Generates a punchy 4-7 word headline hook with a color emoji.
    Uses Gemini API if GEMINI_API_KEY is available; otherwise uses intelligent heuristic fallback.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key and genai:
        prompt = f"""
You are an expert viral gaming shorts & reels editor.
Write a punchy, click-worthy 4 to 6 word ALL-CAPS headline hook with exactly 1 or 2 matching emojis for this clip.
Streamer: {streamer}
Game/Category: {game}
Stream Title: {stream_title}
What Streamer Said: {transcript or 'N/A'}
Top Chat Reactions: {', '.join(sample_chat or [])}

RULES:
- Length: 4 to 6 words only + 1 emoji at the end.
- Must be ALL CAPS.
- DO NOT use quotation marks or prefixes. Just the raw hook.
- Example: XQC REACTS TO SPACEX STARSHIP 🚀
- Example: KAI CENAT CANNOT BELIEVE THIS 💀
- Example: CLIX CLUTCHES WITH 1 HP 🤯
"""
        models_to_try = _get_configured_models()
        client = None
        for model_name in models_to_try:
            try:
                if client is None:
                    client = genai.Client(api_key=api_key)
                resp = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(temperature=0.7, max_output_tokens=30)
                )
                raw = (resp.text or "").strip().replace('"', '').replace("'", "")
                if 3 <= len(raw.split()) <= 10:
                    return raw
            except Exception as e:
                print(f"[!] Gemini model '{model_name}' failed ({e}); falling back to next model...")

    # Rule-based fallback
    lower_context = f"{stream_title} {transcript or ''} {' '.join(sample_chat or [])}".lower()
    chosen_emoji = "🔥"
    for k, emoji in EMOJI_KEYWORDS.items():
        if k in lower_context:
            chosen_emoji = emoji
            break

    if "starship" in lower_context or "spacex" in lower_context or "rocket" in lower_context:
        return f"{streamer.upper()} REACTS TO SPACEX STARSHIP 🚀"
    elif "police" in lower_context or "busted" in lower_context or "chase" in lower_context:
        return f"{streamer.upper()} GETS CHASED BY COPS 🚨"
    elif "clutch" in lower_context or "win" in lower_context or "victory" in lower_context:
        return f"{streamer.upper()} INSANE CLUTCH MOMENT 🏆"
    elif "rage" in lower_context or "screaming" in lower_context:
        return f"{streamer.upper()} CANNOT BELIEVE THIS 💀"
    else:
        game_label = (game or 'STREAM').upper()
        if len(game_label.split()) > 2:
            game_label = game_label.split()[0]
        return f"{streamer.upper()} GOES CRAZY ON {game_label} {chosen_emoji}"


def render_hook_banner(hook_text: str, output_png: str) -> str:
    """
    Renders a 1080x220 transparent PNG banner with the hook text and color emojis.
    Uses Pilmoji to guarantee full-color cross-platform emoji rendering.
    Automatically scales font size to ensure text and emojis stay within safe margins.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_png)), exist_ok=True)
    img = Image.new("RGBA", (1080, 220), (0, 0, 0, 0))

    font_candidates = [
        "arialbd.ttf",
        "LiberationSans-Bold.ttf",
        "DejaVuSans-Bold.ttf",
        "impact.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf"
    ]

    base_font_path = None
    for fc in font_candidates:
        try:
            _ = ImageFont.truetype(fc, 48)
            base_font_path = fc
            break
        except Exception:
            pass

    font_size = 46
    with Pilmoji(img) as p:
        while font_size >= 30:
            if base_font_path:
                font = ImageFont.truetype(base_font_path, font_size)
            else:
                font = ImageFont.load_default()

            try:
                tw, th = p.getsize(hook_text, font=font)
            except Exception:
                bbox = font.getbbox(hook_text)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]

            if tw <= 920 or font_size <= 30:
                break
            font_size -= 2

        tx = max(40, (1080 - tw) // 2)
        ty = max(40, (220 - th) // 2)
        p.text((tx, ty), hook_text, fill=(255, 255, 255, 255), font=font)

    img.save(output_png)
    return output_png
