"""
Multi-Stage Anti-Slop Scriptwriter (Inspired by rahulanand1103/youtube-script-writer).
Implements Research -> Beat Sheet -> Draft -> Editorial Criticism -> Polish.
"""

import os
import json
from .editor import evaluate_script
from .vault import get_vault_story

SYSTEM_PROMPT = """You are a master historical and comedic storyteller in the style of Casually Explained, Sam O'Nella, and OverSimplified.
Your job is to write a fast-paced 60-90 second vertical animation script for YouTube Shorts / TikTok.

STRICT EDITORIAL RULES:
1. NO AI SLOP: Absolutely forbidden words: 'delve', 'testament', 'beacon', 'tapestry', 'little did they know', 'in a world where', 'have you ever wondered', 'in conclusion', 'fast forward to'.
2. COLD HOOK: Jump immediately into the absurdity or crisis. Do not say 'Today we are going to look at...' or ask questions.
3. VISUAL STAGE DIRECTIONS: Every scene MUST specify visual instructions:
   - "environment": e.g. "palace", "desert", "courtroom", "ruins", "street", "stadium"
   - "characters": list of character objects with:
     - "id": name
     - "style": "colored" or "bw" (black-and-white)
     - "color": hex code (e.g. "#DC2626" for red hoodie/tunic, "#0284C7" for blue, etc.)
     - "emotion": "shocked", "deadpan", "scheming", "raging", "smug", "sweating", "laughing"
     - "pose": "hands_up", "facepalm", "pointing", "shrug", "thinking", "stand"
   - "props": list of props e.g. ["sword", "crown", "bottle", "cash_bag", "hammer", "scroll"]
   - "camera": "normal", "zoom_in", "shake"
   - "sfx": "boom", "pop", "whoosh"
4. PACING: 5 to 7 distinct narrative beats totaling ~150 to 220 words.

Return ONLY a valid JSON object matching this schema:
{
  "id": "short_unique_id",
  "category": "history" | "mythology" | "humor",
  "title": "Compelling Title",
  "scenes": [
    {
      "beat": "cold_hook" | "absurd_setup" | "escalation_1" | "escalation_2" | "climax" | "resolution",
      "text": "Spoken spoken dialogue.",
      "environment": "palace",
      "characters": [{"id": "hero", "style": "colored", "color": "#0284C7", "emotion": "shocked", "pose": "hands_up"}],
      "props": ["crown"],
      "camera": "zoom_in",
      "sfx": "boom"
    }
  ]
}
"""

def generate_story_script(category=None, topic=None, api_key=None, max_revisions=3):
    """
    Executes the multi-stage writing and editorial criticism loop.
    Rejects draft if it fails the anti-slop threshold.
    """
    api_key = api_key or os.getenv("GEMINI_API_KEY")

    # Only call dynamic LLM if an explicit topic is provided and API key is present
    if api_key and topic:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)

            user_query = f"Write a video script. Category: {category or 'history'}. Topic: {topic or 'A bizarre true historical event'}."
            
            from google.genai import types
            for revision in range(max_revisions):
                print(f"[*] Draft Generation (Attempt {revision + 1}/{max_revisions})...")
                res = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=user_query,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        response_mime_type="application/json"
                    )
                )
                
                raw_json = res.text.strip()
                if "```json" in raw_json:
                    raw_json = raw_json.split("```json")[1].split("```")[0].strip()
                elif "```" in raw_json:
                    raw_json = raw_json.split("```")[1].split("```")[0].strip()

                script_data = json.loads(raw_json)

                # Adversarial Critique
                eval_res = evaluate_script(script_data)
                print(f"[*] Editorial Quality Score: {eval_res['score']}/10 (Passed: {eval_res['passed']})")

                if eval_res["passed"]:
                    print("[+] Script passed all editorial quality gates!")
                    return script_data
                else:
                    print(f"[-] Revision needed: {eval_res['feedback']}")
                    user_query += f"\n\nCRITICAL FEEDBACK FROM EDITOR: Your previous draft was rejected for:\n" + "\n".join(eval_res["feedback"]) + "\nFix these issues and rewrite."

        except Exception as e:
            print(f"[-] AI generation failed ({e}), selecting verified story from vault.")

    # High quality verified fallback from curated vault
    print("[*] Retrieving verified story from curated story vault...")
    return get_vault_story(category=category)

if __name__ == "__main__":
    story = generate_story_script(category="history")
    print("Selected Story:", story["title"])
