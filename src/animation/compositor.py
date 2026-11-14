"""
Scene Compositor: Combines Environments, Elements (Vehicles, Trees, Buildings),
Multiple Dynamic Characters, Interactive Props, and Camera FX.
"""

import random
from PIL import Image, ImageDraw
from .environments import draw_environment
from .elements import draw_vehicle, draw_nature, draw_architecture
from .character_rig import draw_character
from .bubbles import draw_speech_bubble

WIDTH = 1080
HEIGHT = 1920

def compose_scene_frame(scene_config, frame_idx=0, is_sfx_active=False):
    """
    Renders one full 9:16 frame for a scene.
    scene_config:
      - environment: str
      - elements: list of dicts [{"type": "vehicle"|"nature"|"architecture", "name": "car"|"tree", "x": 500, "y": 1400, "scale": 1.0, "color": "#..."}]
      - characters: list of dicts [{"id": str, "style": "colored"|"bw", "color": str, "emotion": str, "pose": str, "x": int, "y": int}]
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

    # 1. Environment Background
    env_name = scene_config.get("environment", "default")
    draw_environment(draw, env_type=env_name, width=WIDTH, height=HEIGHT)

    # 2. Camera Zoom & Scale
    scale = 1.0
    base_cy = HEIGHT // 2 + 200
    if camera == "zoom_in":
        scale = 1.45
        base_cy = HEIGHT // 2 + 420

    base_cy += offset_y

    # 3. Render Background Elements (Trees, Clouds, Buildings, Vehicles)
    elements = scene_config.get("elements", [])
    
    # Auto-infer elements if not explicitly specified
    if not elements:
        if env_name in ("desert", "dust_road"):
            elements = [
                {"type": "nature", "name": "clouds", "x": 300, "y": 300, "scale": 0.8},
                {"type": "nature", "name": "mountain", "x": 800, "y": 1320, "scale": 0.75}
            ]
        elif env_name == "orchard":
            elements = [
                {"type": "nature", "name": "apple_tree", "x": 220, "y": 1480, "scale": 0.95},
                {"type": "nature", "name": "apple_tree", "x": 860, "y": 1480, "scale": 0.9}
            ]
        elif env_name == "finish_line":
            elements = [
                {"type": "architecture", "name": "finish_banner", "x": WIDTH // 2, "y": 1380, "scale": 1.0}
            ]
        elif env_name in ("paris_street", "hotel_suite"):
            elements = [
                {"type": "architecture", "name": "city_building", "x": 180, "y": 1450, "scale": 0.8},
                {"type": "architecture", "name": "city_building", "x": 900, "y": 1450, "scale": 0.8}
            ]

    for elem in elements:
        etype = elem.get("type", "nature")
        ename = elem.get("name", "tree")
        ex = elem.get("x", 540) + offset_x
        ey = elem.get("y", 1400) + offset_y
        escale = elem.get("scale", 1.0) * (scale if camera == "zoom_in" else 1.0)
        ecolor = elem.get("color", "#DC2626")

        if etype == "vehicle":
            draw_vehicle(draw, vtype=ename, x=ex, y=ey, scale=escale, color=ecolor)
        elif etype == "nature":
            draw_nature(draw, ntype=ename, x=ex, y=ey, scale=escale)
        elif etype == "architecture":
            draw_architecture(draw, btype=ename, x=ex, y=ey, scale=escale, color=ecolor)

    # 4. Position & Render Characters
    chars = scene_config.get("characters", [{"id": "char", "style": "bw", "emotion": "talking", "pose": "stand"}])
    props = scene_config.get("props", [])
    primary_prop = props[0] if props else None

    if len(chars) == 1:
        c = chars[0]
        char_x = c.get("x", WIDTH // 2) + offset_x
        char_y = c.get("y", base_cy)
        draw_character(draw, char_x, char_y, c, frame_idx=frame_idx, scale=scale, active_prop=primary_prop)
    else:
        # Multiple characters
        default_positions = [
            (int(WIDTH * 0.28), base_cy),
            (int(WIDTH * 0.72), base_cy),
            (int(WIDTH * 0.50), base_cy)
        ]
        for idx, c in enumerate(chars):
            def_x, def_y = default_positions[idx % len(default_positions)]
            char_x = c.get("x", def_x) + offset_x
            char_y = c.get("y", def_y)
            prop = primary_prop if idx == 0 else None
            draw_character(draw, char_x, char_y, c, frame_idx=frame_idx, scale=scale, active_prop=prop)

    # 5. Dialogue & Speech Bubbles (Yash-Kavaiya / Manim Actor Style)
    bubble_info = scene_config.get("dialogue_bubble")
    if bubble_info:
        bubble_text = bubble_info.get("text", "!")
        bubble_type = bubble_info.get("type", "speech")
        # Position bubble above primary speaker
        speaker_x = chars[0].get("x", WIDTH // 2) + offset_x
        mouth_xy = (speaker_x, base_cy - int(240 * scale) + int(35 * scale))
        bubble_xy = (speaker_x - int(80 * scale), base_cy - int(380 * scale))
        draw_speech_bubble(draw, bubble_text, mouth_xy, bubble_xy, bubble_type=bubble_type)

    # 6. Impact Burst Lines on SFX hits
    if is_sfx_active:
        cx_burst = WIDTH // 2
        cy_burst = HEIGHT // 2 - 100
        for angle_deg in range(0, 360, 24):
            import math
            rad = math.radians(angle_deg + (frame_idx % 2) * 8)
            p1 = (int(cx_burst + math.cos(rad) * 240), int(cy_burst + math.sin(rad) * 240))
            p2 = (int(cx_burst + math.cos(rad) * 400), int(cy_burst + math.sin(rad) * 400))
            draw.line([p1, p2], fill=(148, 163, 184), width=6)

    return img
