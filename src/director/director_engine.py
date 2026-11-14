"""
Autonomous Stickman Video Director Engine (Inspired by kaomei/stickman-video-director).
Provides Director Mode & Autopilot Mode:
- Production Locks (Aesthetic consistency, line weights, color palettes across cuts)
- Multi-Style Art Direction (Modern Pop, Historical Cartoon, Minimal B&W)
- Visual Metaphor & Dialogue Choreography (Speech/Thought Bubbles, Staging)
"""

import os
import json

STYLES = {
    "modern_pop": {
        "line_color": (20, 20, 24),
        "primary_character_color": "#2563EB", # Vibrant Blue
        "secondary_character_color": "#DC2626", # Vibrant Red
        "bg_color": (248, 250, 252),
        "accent_highlight": "#FACC15"
    },
    "historical_cartoon": {
        "line_color": (30, 25, 20),
        "primary_character_color": "#B45309", # Warm Amber
        "secondary_character_color": "#047857", # Emerald
        "bg_color": (250, 248, 244),
        "accent_highlight": "#E11D48"
    },
    "classic_bw": {
        "line_color": (15, 23, 42),
        "primary_character_color": "#000000",
        "secondary_character_color": "#475569",
        "bg_color": (255, 255, 255),
        "accent_highlight": "#000000"
    }
}

class StickmanDirector:
    def __init__(self, style_mode="historical_cartoon"):
        self.style_mode = style_mode if style_mode in STYLES else "historical_cartoon"
        self.config = STYLES[self.style_mode]

    def direct_treatment(self, raw_story):
        """
        Applies Director Production Locks and visual choreography
        to transform a story draft into an executable multi-beat manifest.
        """
        scenes = raw_story.get("scenes", [])
        directed_scenes = []

        for idx, sc in enumerate(scenes):
            scene_copy = dict(sc)
            
            # Apply Production Color Locks
            chars = scene_copy.get("characters", [])
            for c_idx, c in enumerate(chars):
                if c.get("style") == "colored":
                    if c_idx == 0:
                        c["color"] = self.config["primary_character_color"]
                    else:
                        c["color"] = self.config["secondary_character_color"]

            # Layout-aware dialogue bubbles
            text = sc.get("text", "")
            if "said" in text.lower() or "told" in text.lower() or "?" in text or "!" in text:
                # Add speech/thought bubble for high impact lines
                short_quote = text.split(".")[0][:25]
                if "?" in short_quote:
                    short_quote = "Wait, what?!"
                scene_copy["dialogue_bubble"] = {
                    "text": short_quote.upper(),
                    "type": "thought" if "whisper" in text.lower() or "thought" in text.lower() else "speech"
                }

            directed_scenes.append(scene_copy)

        manifest = {
            "title": raw_story.get("title", "Stickman Short"),
            "style_mode": self.style_mode,
            "production_locks": {
                "aspect_ratio": "9:16",
                "width": 1080,
                "height": 1920,
                "fps": 8,
                "palette": self.config
            },
            "scenes": directed_scenes
        }
        return manifest

if __name__ == "__main__":
    director = StickmanDirector("modern_pop")
    print("Director initialized with Modern Pop palette:", director.config)
