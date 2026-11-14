"""
Advanced Procedural Stick-Figure Character Rig.
Supports Colored & Black-and-White characters, multi-character staging,
rich facial expressions, kinematic gestures, and prop interaction.
"""

import math
import random
from PIL import ImageDraw
from .props import draw_prop

INK_BLACK = (24, 24, 27)

def draw_character(draw, cx, cy, char_config, frame_idx=0, scale=1.0, active_prop=None):
    """
    Renders one stick figure at (cx, cy).
    char_config schema:
      - style: "colored" | "bw"
      - color: hex string (e.g. "#DC2626") or tuple
      - emotion: "shocked", "deadpan", "scheming", "raging", "smug", "sweating", "laughing", "chewing", "talking"
      - pose: "hands_up", "facepalm", "pointing", "shrug", "thinking", "stand"
    """
    style = char_config.get("style", "bw")
    color = char_config.get("color", "#2563EB")
    emotion = char_config.get("emotion", "talking")
    pose = char_config.get("pose", "stand")

    # Parse color
    if isinstance(color, str) and color.startswith("#"):
        c_fill = tuple(int(color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
    else:
        c_fill = color

    line_w = int(14 * scale)
    head_r = int(80 * scale)
    spine_len = int(260 * scale)

    # Line boil / hand-drawn jitter
    random.seed(frame_idx * 13 + hash(char_config.get("id", "char")))
    jx = random.randint(-2, 2)
    jy = random.randint(-2, 2)
    cx += jx
    cy += jy

    head_cy = cy - int(240 * scale)
    neck = (cx, head_cy + head_r)
    pelvis = (cx, neck[1] + spine_len)

    # Colored character torso (Hoodie / Tunic / Armor)
    if style == "colored":
        # Draw colored torso tunic
        torso_box = [cx - int(45 * scale), neck[1], cx + int(45 * scale), pelvis[1]]
        draw.rounded_rectangle(torso_box, radius=int(18 * scale), fill=c_fill, outline=INK_BLACK, width=int(6 * scale))
    else:
        # Classic B&W spine
        draw.line([neck, pelvis], fill=INK_BLACK, width=line_w)

    # Head Circle
    head_box = [cx - head_r, head_cy - head_r, cx + head_r, head_cy + head_r]
    head_fill = (255, 255, 255)
    draw.ellipse(head_box, fill=head_fill, outline=INK_BLACK, width=line_w)

    # Crown / Hair accent for colored characters
    if style == "colored":
        # Colored beanie / hair tuft
        draw.arc([cx - head_r, head_cy - head_r - 8, cx + head_r, head_cy], 180, 360, fill=c_fill, width=int(16 * scale))

    # Facial Expressions
    eye_y = head_cy - int(12 * scale)
    eye_spacing = int(36 * scale)

    if emotion == "shocked":
        for side in [-1, 1]:
            ex = cx + side * eye_spacing
            draw.ellipse([ex - 22, eye_y - 22, ex + 22, eye_y + 22], outline=INK_BLACK, fill=(255, 255, 255), width=line_w - 4)
            draw.ellipse([ex - 6, eye_y - 6, ex + 6, eye_y + 6], fill=INK_BLACK)
        # Drop jaw
        draw.ellipse([cx - 26, head_cy + 25, cx + 26, head_cy + 75], fill=INK_BLACK)

    elif emotion == "deadpan":
        # Half lidded / unamused eyes
        for side in [-1, 1]:
            ex = cx + side * eye_spacing
            draw.line([(ex - 18, eye_y - 4), (ex + 18, eye_y - 4)], fill=INK_BLACK, width=line_w - 2)
            draw.ellipse([ex - 6, eye_y - 2, ex + 6, eye_y + 10], fill=INK_BLACK)
        # Flat straight mouth
        draw.line([(cx - 24, head_cy + 40), (cx + 24, head_cy + 40)], fill=INK_BLACK, width=line_w - 4)

    elif emotion == "scheming":
        # Slanted eyebrows + sideways smirk
        draw.line([(cx - eye_spacing - 18, eye_y - 28), (cx - 10, eye_y - 14)], fill=INK_BLACK, width=line_w - 4)
        draw.line([(cx + 10, eye_y - 14), (cx + eye_spacing + 18, eye_y - 28)], fill=INK_BLACK, width=line_w - 4)
        for side in [-1, 1]:
            ex = cx + side * eye_spacing
            draw.ellipse([ex + 2, eye_y - 8, ex + 14, eye_y + 4], fill=INK_BLACK)
        # Smirk
        draw.arc([cx - 10, head_cy + 25, cx + 35, head_cy + 60], 0, 180, fill=INK_BLACK, width=line_w - 4)

    elif emotion == "raging":
        # Angry V eyebrows
        draw.line([(cx - eye_spacing - 24, eye_y - 36), (cx - 8, eye_y - 16)], fill=INK_BLACK, width=line_w)
        draw.line([(cx + eye_spacing + 24, eye_y - 36), (cx + 8, eye_y - 16)], fill=INK_BLACK, width=line_w)
        for side in [-1, 1]:
            draw.ellipse([cx + side * eye_spacing - 10, eye_y - 6, cx + side * eye_spacing + 10, eye_y + 14], fill=INK_BLACK)
        # Open yelling mouth with grit teeth
        draw.rectangle([cx - 32, head_cy + 30, cx + 32, head_cy + 65], fill=(255, 255, 255), outline=INK_BLACK, width=line_w - 4)
        draw.line([(cx - 30, head_cy + 47), (cx + 30, head_cy + 47)], fill=INK_BLACK, width=4)

    elif emotion == "sweating":
        # Glancing eyes + giant blue sweat bead
        for side in [-1, 1]:
            ex = cx + side * eye_spacing
            draw.ellipse([ex - 14, eye_y - 14, ex + 14, eye_y + 14], outline=INK_BLACK, fill=(255, 255, 255), width=line_w - 4)
            draw.ellipse([ex + 2, eye_y - 6, ex + 12, eye_y + 4], fill=INK_BLACK)
        draw.line([(cx - 25, head_cy + 42), (cx + 25, head_cy + 46)], fill=INK_BLACK, width=line_w - 4)
        # Giant blue sweat teardrop
        draw.ellipse([cx + head_r + 8, head_cy - 20, cx + head_r + 26, head_cy + 6], fill=(56, 189, 248))

    elif emotion == "laughing":
        # Closed curved eyes
        for side in [-1, 1]:
            ex = cx + side * eye_spacing
            draw.arc([ex - 18, eye_y - 12, ex + 18, eye_y + 12], 190, 350, fill=INK_BLACK, width=line_w - 2)
        # Grinning mouth
        draw.chord([cx - 36, head_cy + 25, cx + 36, head_cy + 75], 0, 180, fill=(255, 255, 255), outline=INK_BLACK, width=line_w - 4)

    else:
        # Default talking
        for side in [-1, 1]:
            draw.ellipse([cx + side * eye_spacing - 12, eye_y - 12, cx + side * eye_spacing + 12, eye_y + 12], fill=INK_BLACK)
        m_cycle = abs(math.sin(frame_idx * 1.1))
        m_h = int(m_cycle * 22) + 4
        if m_h > 9:
            draw.ellipse([cx - 22, head_cy + 35 - m_h // 2, cx + 22, head_cy + 35 + m_h // 2], fill=INK_BLACK)
        else:
            draw.line([(cx - 20, head_cy + 35), (cx + 20, head_cy + 35)], fill=INK_BLACK, width=line_w - 4)

    # Limbs Posing
    t = frame_idx * 0.8
    r_hand_pos = None

    if pose == "hands_up":
        l_hand = (cx - int(160 * scale), neck[1] - int(120 * scale) + int(math.sin(t) * 15))
        r_hand = (cx + int(160 * scale), neck[1] - int(120 * scale) - int(math.sin(t) * 15))
        draw.line([neck, (cx - int(110 * scale), neck[1] - int(20 * scale)), l_hand], fill=INK_BLACK, width=line_w)
        draw.line([neck, (cx + int(110 * scale), neck[1] - int(20 * scale)), r_hand], fill=INK_BLACK, width=line_w)
        r_hand_pos = r_hand

    elif pose == "facepalm":
        l_hand = (cx - int(130 * scale), neck[1] + int(140 * scale))
        r_hand = (cx + int(25 * scale), head_cy + int(15 * scale))
        draw.line([neck, (cx - int(100 * scale), neck[1] + int(70 * scale)), l_hand], fill=INK_BLACK, width=line_w)
        draw.line([neck, (cx + int(100 * scale), neck[1] + int(40 * scale)), r_hand], fill=INK_BLACK, width=line_w)

    elif pose == "pointing":
        l_hand = (cx - int(120 * scale), neck[1] + int(120 * scale))
        r_hand = (cx + int(240 * scale), neck[1] - int(20 * scale))
        draw.line([neck, (cx - int(90 * scale), neck[1] + int(60 * scale)), l_hand], fill=INK_BLACK, width=line_w)
        draw.line([neck, (cx + int(120 * scale), neck[1] + int(10 * scale)), r_hand], fill=INK_BLACK, width=line_w)
        r_hand_pos = r_hand

    elif pose == "shrug":
        l_hand = (cx - int(170 * scale), neck[1] - int(15 * scale))
        r_hand = (cx + int(170 * scale), neck[1] - int(15 * scale))
        draw.line([neck, (cx - int(120 * scale), neck[1] + int(35 * scale)), l_hand], fill=INK_BLACK, width=line_w)
        draw.line([neck, (cx + int(120 * scale), neck[1] + int(35 * scale)), r_hand], fill=INK_BLACK, width=line_w)
        r_hand_pos = r_hand

    else:
        # Relaxed conversational stand
        l_hand = (cx - int(140 * scale), neck[1] + int(150 * scale) + int(math.sin(t) * 15))
        r_hand = (cx + int(140 * scale), neck[1] + int(150 * scale) - int(math.sin(t) * 15))
        draw.line([neck, (cx - int(100 * scale), neck[1] + int(70 * scale)), l_hand], fill=INK_BLACK, width=line_w)
        draw.line([neck, (cx + int(100 * scale), neck[1] + int(70 * scale)), r_hand], fill=INK_BLACK, width=line_w)
        r_hand_pos = r_hand

    # Legs
    leg_len = int(320 * scale)
    l_foot = (cx - int(80 * scale), pelvis[1] + leg_len)
    r_foot = (cx + int(80 * scale), pelvis[1] + leg_len)
    draw.line([pelvis, l_foot], fill=INK_BLACK, width=line_w)
    draw.line([pelvis, r_foot], fill=INK_BLACK, width=line_w)

    # Render Prop in character's hand if specified
    if active_prop and r_hand_pos:
        draw_prop(draw, active_prop, r_hand_pos[0] + int(20 * scale), r_hand_pos[1] - int(10 * scale), scale=scale)
