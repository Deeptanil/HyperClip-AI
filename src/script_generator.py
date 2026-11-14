"""
Script Generator for ChainsFR-style Stickman Storytime Videos.
Supports both LLM API generation (Gemini / Groq / OpenAI) and high-converting built-in viral templates.
"""

import os
import json
import random

VIRAL_TEMPLATES = [
    {
        "title": "Why Humans Are Actually Weird",
        "scenes": [
            {
                "text": "Bro, why do humans do this? You're walking down the hallway, and you make eye contact with someone you kinda know.",
                "emotion": "talking",
                "pose": "hands_up",
                "camera": "normal",
                "sfx": "whoosh"
            },
            {
                "text": "Now you have two terrible choices: do the awkward head nod, or stare at the floor like you just discovered gravity.",
                "emotion": "awkward",
                "pose": "facepalm",
                "camera": "normal",
                "sfx": "pop"
            },
            {
                "text": "And don't get me started on when you both move in the same direction to get out of the way.",
                "emotion": "shocked",
                "pose": "shrug",
                "camera": "zoom_in",
                "sfx": "pop"
            },
            {
                "text": "Suddenly you're in a high stakes salsa dance with a complete stranger in front of the school bathroom.",
                "emotion": "laughing",
                "pose": "hands_up",
                "camera": "shake",
                "sfx": "boom"
            },
            {
                "text": "Like just let me dissolve into the wall bro. Subscribe if you do this every single day.",
                "emotion": "facepalm",
                "pose": "facepalm",
                "camera": "normal",
                "sfx": "whoosh"
            }
        ]
    },
    {
        "title": "The Fake Phone Call Trick",
        "scenes": [
            {
                "text": "Bro, tell me I'm not the only person who pulls out their phone and pretends to be busy to avoid someone.",
                "emotion": "talking",
                "pose": "hands_up",
                "camera": "normal",
                "sfx": "whoosh"
            },
            {
                "text": "You see someone you don't wanna talk to, and suddenly you're intensely reading the calculator app like it's Shakespeare.",
                "emotion": "thinking",
                "pose": "shrug",
                "camera": "normal",
                "sfx": "pop"
            },
            {
                "text": "Then the ultimate disaster happens. Your phone actually rings while it's literally pressed against your ear.",
                "emotion": "shocked",
                "pose": "hands_up",
                "camera": "zoom_in",
                "sfx": "boom"
            },
            {
                "text": "The sheer panic in that moment could power a small European country for three weeks.",
                "emotion": "angry",
                "pose": "facepalm",
                "camera": "shake",
                "sfx": "boom"
            },
            {
                "text": "Now you just gotta pack your bags and move to Antarctica. Don't lie, you've done this before.",
                "emotion": "laughing",
                "pose": "pointing",
                "camera": "normal",
                "sfx": "whoosh"
            }
        ]
    },
    {
        "title": "The Blanket Thermostat War",
        "scenes": [
            {
                "text": "Why is sleeping at night a full tactical mission? You put one leg out of the blanket to cool down.",
                "emotion": "talking",
                "pose": "hands_up",
                "camera": "normal",
                "sfx": "whoosh"
            },
            {
                "text": "Now you're the perfect temperature. But your brain whispers: the closet demon now has legal rights to grab your foot.",
                "emotion": "thinking",
                "pose": "facepalm",
                "camera": "normal",
                "sfx": "pop"
            },
            {
                "text": "So you pull the leg back in. Now you're literally baking in an oven at 400 degrees Fahrenheit.",
                "emotion": "angry",
                "pose": "hands_up",
                "camera": "zoom_in",
                "sfx": "pop"
            },
            {
                "text": "It's either heat stroke or getting eaten alive by a mythical creature. Why is there no middle ground?",
                "emotion": "shocked",
                "pose": "shrug",
                "camera": "shake",
                "sfx": "boom"
            },
            {
                "text": "Drop a follow if you sacrifice your comfort to survive the bedroom monster.",
                "emotion": "laughing",
                "pose": "pointing",
                "camera": "normal",
                "sfx": "whoosh"
            }
        ]
    }
]

def generate_script(topic=None, api_key=None, provider="template"):
    """
    Generates a ChainsFR style script.
    If Gemini/Groq key is provided, generates dynamic AI script.
    Otherwise picks a tested viral script template.
    """
    if provider == "gemini" and api_key:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            prompt = f"""
Write a 20-30 second high-energy comedy stickman script in the exact style of ChainsFR or Casually Explained.
Topic: {topic or 'relatable awkward daily moments'}
Formatting requirements:
Return ONLY valid JSON with this exact structure:
{{
  "title": "Short title",
  "scenes": [
    {{
      "text": "1-2 punchy spoken sentences.",
      "emotion": "talking" | "shocked" | "awkward" | "angry" | "thinking" | "laughing" | "facepalm",
      "pose": "stand" | "hands_up" | "shrug" | "facepalm" | "pointing",
      "camera": "normal" | "zoom_in" | "shake",
      "sfx": "whoosh" | "pop" | "boom" | null
    }}
  ]
}}
Keep total duration around 20-25 seconds (4 to 5 scenes max).
Make it funny, fast-paced, relatable, and use fast storytelling slang ("Bro", "Literally", etc.).
"""
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            text = response.text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            return json.loads(text)
        except Exception as e:
            print(f"Warning: Gemini generation failed ({e}), falling back to viral template.")

    # Pick random viral template
    template = random.choice(VIRAL_TEMPLATES)
    return template

if __name__ == "__main__":
    script = generate_script()
    print(json.dumps(script, indent=2))
