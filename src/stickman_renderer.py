"""
Stickman Stop-Motion Procedural Renderer.
Renders high-res 1080x1920 vertical frames with hand-drawn line boiling,
expressive faces, dynamic poses, camera zooms, and visual FX.
"""

import math
import random
from PIL import Image, ImageDraw

WIDTH = 1080
HEIGHT = 1920
BG_COLOR = (250, 248, 244)  # Warm paper-white background
INK_COLOR = (24, 24, 27)     # Deep charcoal ink
ACCENT_BLUE = (56, 189, 248) # Sweat bead / accent
ACCENT_RED = (239, 68, 68)   # Anger mark / accent

def get_jitter(seed, amount=2):
    """Generates authentic hand-drawn line boiling / stop-motion jitter."""
    random.seed(seed)
    return random.randint(-amount, amount), random.randint(-amount, amount)

def draw_wobbly_line(draw, points, color=INK_COLOR, width=14, seed=0):
    """Draws a slightly organic hand-drawn line with subtle micro-bends."""
    if len(points) < 2:
        return
    p1, p2 = points[0], points[1]
    jx, jy = get_jitter(seed, 2)
    mid = ((p1[0] + p2[0]) // 2 + jx, (p1[1] + p2[1]) // 2 + jy)
    draw.line([p1, mid, p2], fill=color, width=width, joint="curve")

def draw_head_and_face(draw, cx, cy, radius, emotion, frame_idx, line_w=14):
    """Renders expressive ChainsFR-style cartoon face."""
    jx, jy = get_jitter(frame_idx * 17, 2)
    cx += jx
    cy += jy

    # Head circle
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], outline=INK_COLOR, width=line_w)

    eye_y = cy - 15
    eye_spacing = 42

    # Emotion-based facial features
    if emotion == "shocked":
        # Huge wide eyes with tiny pupils
        for side in [-1, 1]:
            ex = cx + side * eye_spacing
            draw.ellipse([ex - 24, eye_y - 24, ex + 24, eye_y + 24], outline=INK_COLOR, fill=(255, 255, 255), width=line_w - 4)
            draw.ellipse([ex - 6, eye_y - 6, ex + 6, eye_y + 6], fill=INK_COLOR)
        # Drop jaw mouth
        draw.ellipse([cx - 28, cy + 30, cx + 28, cy + 85], outline=INK_COLOR, fill=INK_COLOR)

    elif emotion == "awkward":
        # Glancing eyes + sweat bead
        for side in [-1, 1]:
            ex = cx + side * eye_spacing
            draw.ellipse([ex - 16, eye_y - 16, ex + 16, eye_y + 16], outline=INK_COLOR, fill=(255, 255, 255), width=line_w - 4)
            draw.ellipse([ex + 2, eye_y - 8, ex + 14, eye_y + 4], fill=INK_COLOR)
        # Squiggly mouth
        draw.line([
            (cx - 35, cy + 45), (cx - 15, cy + 50),
            (cx + 5, cy + 42), (cx + 35, cy + 48)
        ], fill=INK_COLOR, width=line_w - 4, joint="curve")
        # Sweat bead on temple
        draw.ellipse([cx + radius + 10, cy - 20, cx + radius + 26, cy + 6], fill=ACCENT_BLUE)

    elif emotion == "angry":
        # Slanted eyebrows
        draw.line([(cx - eye_spacing - 25, eye_y - 35), (cx - 10, eye_y - 15)], fill=INK_COLOR, width=line_w)
        draw.line([(cx + eye_spacing + 25, eye_y - 35), (cx + 10, eye_y - 15)], fill=INK_COLOR, width=line_w)
        # Glaring eyes
        for side in [-1, 1]:
            ex = cx + side * eye_spacing
            draw.ellipse([ex - 12, eye_y - 8, ex + 12, eye_y + 14], fill=INK_COLOR)
        # Scowl mouth
        draw.line([(cx - 30, cy + 55), (cx, cy + 40), (cx + 30, cy + 55)], fill=INK_COLOR, width=line_w - 2)

    elif emotion == "laughing":
        # Closed curved eyes (^ ^)
        for side in [-1, 1]:
            ex = cx + side * eye_spacing
            draw.arc([ex - 20, eye_y - 15, ex + 20, eye_y + 15], 190, 350, fill=INK_COLOR, width=line_w - 2)
        # Big open grin with teeth
        mouth_box = [cx - 40, cy + 25, cx + 40, cy + 75]
        draw.chord(mouth_box, 0, 180, fill=(255, 255, 255), outline=INK_COLOR, width=line_w - 4)
        draw.line([(cx - 36, cy + 50), (cx + 36, cy + 50)], fill=INK_COLOR, width=6)

    elif emotion == "thinking":
        # One eyebrow raised
        draw.arc([cx - eye_spacing - 20, eye_y - 40, cx - eye_spacing + 20, eye_y - 20], 180, 360, fill=INK_COLOR, width=line_w - 4)
        draw.line([(cx + eye_spacing - 20, eye_y - 25), (cx + eye_spacing + 20, eye_y - 25)], fill=INK_COLOR, width=line_w - 4)
        # Looking up-right pupils
        for side in [-1, 1]:
            ex = cx + side * eye_spacing
            draw.ellipse([ex - 15, eye_y - 15, ex + 15, eye_y + 15], outline=INK_COLOR, fill=(255, 255, 255), width=line_w - 4)
            draw.ellipse([ex + 2, eye_y - 12, ex + 12, eye_y - 2], fill=INK_COLOR)
        # Pondering small mouth
        draw.line([(cx - 15, cy + 45), (cx + 20, cy + 40)], fill=INK_COLOR, width=line_w - 4)

    else:
        # Default talking / neutral
        for side in [-1, 1]:
            ex = cx + side * eye_spacing
            draw.ellipse([ex - 12, eye_y - 12, ex + 12, eye_y + 12], fill=INK_COLOR)
        # Animated talking mouth cycle (8 fps cadence)
        mouth_cycle = abs(math.sin(frame_idx * 1.2))
        m_height = int(mouth_cycle * 26) + 4
        if m_height > 10:
            draw.ellipse([cx - 24, cy + 35 - m_height // 2, cx + 24, cy + 35 + m_height // 2], fill=INK_COLOR)
        else:
            draw.line([(cx - 22, cy + 35), (cx + 22, cy + 35)], fill=INK_COLOR, width=line_w - 4)

def render_stickman_frame(frame_idx, emotion="talking", pose="hands_up", camera="normal", is_sfx_active=False):
    """
    Renders one full 1080x1920 stop-motion stickman frame.
    """
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Base scale and center
    scale = 1.0
    cx = WIDTH // 2
    cy = HEIGHT // 2 + 100

    if camera == "zoom_in":
        scale = 1.55
        cy = HEIGHT // 2 + 350
    elif camera == "shake":
        shake_x = random.randint(-18, 18)
        shake_y = random.randint(-18, 18)
        cx += shake_x
        cy += shake_y

    head_radius = int(85 * scale)
    line_w = int(14 * scale)
    spine_len = int(280 * scale)

    head_center_y = cy - int(240 * scale)
    neck = (cx, head_center_y + head_radius)
    pelvis = (cx, neck[1] + spine_len)

    # Background Speed Lines / Action burst if shocked or boom
    if camera == "shake" or is_sfx_active:
        for angle in range(0, 360, 20):
            rad = math.radians(angle + (frame_idx % 3) * 5)
            r1 = int(head_radius * 2.2)
            r2 = int(head_radius * 3.8)
            p_start = (int(cx + math.cos(rad) * r1), int(head_center_y + math.sin(rad) * r1))
            p_end = (int(cx + math.cos(rad) * r2), int(head_center_y + math.sin(rad) * r2))
            draw.line([p_start, p_end], fill=(220, 218, 212), width=6)

    # Draw Head & Facial Expressions
    draw_head_and_face(draw, cx, head_center_y, head_radius, emotion, frame_idx, line_w)

    # Draw Spine
    draw_wobbly_line(draw, [neck, pelvis], width=line_w, seed=frame_idx)

    # Draw Arms based on Pose
    t = frame_idx * 0.8
    if pose == "hands_up":
        # Excited / panicked hands thrown up
        l_elbow = (cx - int(120 * scale), neck[1] - int(20 * scale) + int(math.sin(t) * 15))
        l_hand = (cx - int(170 * scale), neck[1] - int(130 * scale) + int(math.cos(t) * 20))
        r_elbow = (cx + int(120 * scale), neck[1] - int(20 * scale) - int(math.sin(t) * 15))
        r_hand = (cx + int(170 * scale), neck[1] - int(130 * scale) - int(math.cos(t) * 20))
        draw_wobbly_line(draw, [neck, l_elbow, l_hand], width=line_w, seed=frame_idx + 1)
        draw_wobbly_line(draw, [neck, r_elbow, r_hand], width=line_w, seed=frame_idx + 2)

    elif pose == "facepalm":
        # One hand covering face
        l_elbow = (cx - int(110 * scale), neck[1] + int(80 * scale))
        l_hand = (cx - int(140 * scale), neck[1] + int(160 * scale))
        r_elbow = (cx + int(110 * scale), neck[1] + int(40 * scale))
        r_hand = (cx + int(20 * scale), head_center_y + int(10 * scale))
        draw_wobbly_line(draw, [neck, l_elbow, l_hand], width=line_w, seed=frame_idx + 1)
        draw_wobbly_line(draw, [neck, r_elbow, r_hand], width=line_w, seed=frame_idx + 2)

    elif pose == "pointing":
        # Pointing outward
        l_elbow = (cx - int(100 * scale), neck[1] + int(60 * scale))
        l_hand = (cx - int(130 * scale), neck[1] + int(140 * scale))
        r_elbow = (cx + int(120 * scale), neck[1] + int(10 * scale))
        r_hand = (cx + int(240 * scale), neck[1] - int(10 * scale))
        draw_wobbly_line(draw, [neck, l_elbow, l_hand], width=line_w, seed=frame_idx + 1)
        draw_wobbly_line(draw, [neck, r_elbow, r_hand], width=line_w, seed=frame_idx + 2)

    elif pose == "shrug":
        # Classic shrug pose
        l_elbow = (cx - int(130 * scale), neck[1] + int(40 * scale))
        l_hand = (cx - int(180 * scale), neck[1] - int(20 * scale))
        r_elbow = (cx + int(130 * scale), neck[1] + int(40 * scale))
        r_hand = (cx + int(180 * scale), neck[1] - int(20 * scale))
        draw_wobbly_line(draw, [neck, l_elbow, l_hand], width=line_w, seed=frame_idx + 1)
        draw_wobbly_line(draw, [neck, r_elbow, r_hand], width=line_w, seed=frame_idx + 2)

    else:
        # Default conversational gesturing
        l_elbow = (cx - int(110 * scale), neck[1] + int(70 * scale) + int(math.sin(t) * 20))
        l_hand = (cx - int(150 * scale), neck[1] + int(160 * scale) + int(math.cos(t) * 25))
        r_elbow = (cx + int(110 * scale), neck[1] + int(70 * scale) - int(math.sin(t) * 20))
        r_hand = (cx + int(150 * scale), neck[1] + int(160 * scale) - int(math.cos(t) * 25))
        draw_wobbly_line(draw, [neck, l_elbow, l_hand], width=line_w, seed=frame_idx + 1)
        draw_wobbly_line(draw, [neck, r_elbow, r_hand], width=line_w, seed=frame_idx + 2)

    # Draw Legs (only visible if camera is normal)
    if camera != "zoom_in":
        leg_len = int(320 * scale)
        l_foot = (cx - int(90 * scale), pelvis[1] + leg_len)
        r_foot = (cx + int(90 * scale), pelvis[1] + leg_len)
        draw_wobbly_line(draw, [pelvis, l_foot], width=line_w, seed=frame_idx + 3)
        draw_wobbly_line(draw, [pelvis, r_foot], width=line_w, seed=frame_idx + 4)

    return img

if __name__ == "__main__":
    frame = render_stickman_frame(0, emotion="shocked", pose="hands_up", camera="zoom_in")
    frame.save("test_frame.png")
    print("Test frame saved as test_frame.png")
