"""
Scene Compositor: Combines Environments, Multiple Characters, Props, and Camera FX
into a coherent 1080x1920 vertical video frame.
"""

import random
from PIL import Image, ImageDraw
from .environments import draw_environment
from .character_rig import draw_character

WIDTH = 1080
HEIGHT = 1920

def compose_scene_frame(scene_config, frame_idx=0, is_sfx_active=False):
    """
    Renders one full 9:16 frame for a scene.
    scene_config:
      - environment: str
      - characters: list of dicts
      - props: list of str
      - camera: "normal" | "zoom_in" | "shake"
    """
    img = Image.new("RGB", (WIDTH, HEIGHT), (250, 248, 244))
    draw = ImageDraw.Draw(img)

    camera = scene_config.get("camera", "normal")
    offset_x, offset_y = 0, 0

    if camera == "shake" or (is_sfx_active and scene_config.get("sfx") == "boom"):
        offset_x = random.randint(-18, 18)
        offset_y = random.randint(-18, 18)

    # 1. Draw Environment / Background Layer
    env_name = scene_config.get("environment", "default")
    draw_environment(draw, env_type=env_name, width=WIDTH, height=HEIGHT)

    # 2. Camera Zoom & Scale
    scale = 1.0
    base_cy = HEIGHT // 2 + 200
    if camera == "zoom_in":
        scale = 1.45
        base_cy = HEIGHT // 2 + 420

    base_cy += offset_y

    # 3. Position Characters
    chars = scene_config.get("characters", [{"id": "char", "style": "bw", "emotion": "talking", "pose": "stand"}])
    props = scene_config.get("props", [])
    primary_prop = props[0] if props else None

    if len(chars) == 1:
        # Single character centered
        cx = WIDTH // 2 + offset_x
        draw_character(draw, cx, base_cy, chars[0], frame_idx=frame_idx, scale=scale, active_prop=primary_prop)
    else:
        # Two characters interacting (facing each other)
        c1_x = int(WIDTH * 0.32) + offset_x
        c2_x = int(WIDTH * 0.68) + offset_x
        draw_character(draw, c1_x, base_cy, chars[0], frame_idx=frame_idx, scale=scale, active_prop=primary_prop)
        draw_character(draw, c2_x, base_cy, chars[1], frame_idx=frame_idx, scale=scale, active_prop=None)

    # 4. Impact Burst Lines on SFX hits
    if is_sfx_active:
        cx_burst = WIDTH // 2
        cy_burst = HEIGHT // 2 - 100
        for angle_deg in range(0, 360, 24):
            import math
            rad = math.radians(angle_deg + (frame_idx % 2) * 8)
            p1 = (int(cx_burst + math.cos(rad) * 220), int(cy_burst + math.sin(rad) * 220))
            p2 = (int(cx_burst + math.cos(rad) * 380), int(cy_burst + math.sin(rad) * 380))
            draw.line([p1, p2], fill=(148, 163, 184), width=6)

    return img

if __name__ == "__main__":
    test_scene = {
        "environment": "palace",
        "camera": "normal",
        "characters": [
            {"id": "thor", "style": "colored", "color": "#DC2626", "emotion": "raging", "pose": "hands_up"},
            {"id": "heimdall", "style": "colored", "color": "#F59E0B", "emotion": "scheming", "pose": "pointing"}
        ],
        "props": ["hammer"]
    }
    frame = compose_scene_frame(test_scene, frame_idx=0)
    frame.save("test_composite.png")
    print("Composite frame saved to test_composite.png")
