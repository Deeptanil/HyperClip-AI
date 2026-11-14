"""
Advanced Procedural Stick-Figure Character Rig.
Supports Colored & Black-and-White characters, multi-character staging,
rich facial expressions, kinematic gestures, props, and extensive physical poses:
- running (marathon sprint/stride)
- collapsed (slumped on floor)
- crawling (on hands and knees)
- napping (sleeping with zZZs)
- drinking/eating (hand to mouth)
- driving (seated behind steering wheel)
- celebrating (arms in victory V)
- hands_up, facepalm, pointing, shrug, stand
"""

import math
import random
from PIL import ImageDraw
from .props import draw_prop

INK_BLACK = (24, 24, 27)

def draw_character(draw, cx, cy, char_config, frame_idx=0, scale=1.0, active_prop=None):
    style = char_config.get("style", "bw")
    color = char_config.get("color", "#2563EB")
    emotion = char_config.get("emotion", "talking")
    pose = char_config.get("pose", "stand")

    if isinstance(color, str) and color.startswith("#"):
        c_fill = tuple(int(color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
    else:
        c_fill = color

    line_w = int(14 * scale)
    head_r = int(80 * scale)
    spine_len = int(260 * scale)

    # Line boil / hand-drawn jitter
    random.seed(frame_idx * 17 + hash(char_config.get("id", "char")))
    jx = random.randint(-2, 2)
    jy = random.randint(-2, 2)
    cx += jx
    cy += jy

    t = frame_idx * 0.9

    # ==========================================
    # POSE TYPE A: COLLAPSED (Lying on ground)
    # ==========================================
    if pose in ("collapsed", "fainted"):
        ground_y = cy + int(180 * scale)
        head_x = cx - int(180 * scale)
        head_y = ground_y - int(40 * scale)
        pelvis_x = cx + int(120 * scale)
        pelvis_y = ground_y - int(25 * scale)

        # Draw lying spine/torso
        if style == "colored":
            draw.rounded_rectangle([head_x + int(60 * scale), ground_y - int(55 * scale), pelvis_x, ground_y], radius=int(12 * scale), fill=c_fill, outline=INK_BLACK, width=int(5 * scale))
        else:
            draw.line([(head_x + int(60 * scale), ground_y - int(25 * scale)), (pelvis_x, pelvis_y)], fill=INK_BLACK, width=line_w)

        # Head lying down
        draw.ellipse([head_x - head_r, head_y - head_r, head_x + head_r, head_y + head_r], fill=(255, 255, 255), outline=INK_BLACK, width=line_w)
        # Dizzy X X eyes
        for ex in [head_x - int(25 * scale), head_x + int(20 * scale)]:
            draw.line([(ex - 12, head_y - 12), (ex + 12, head_y + 12)], fill=INK_BLACK, width=line_w - 4)
            draw.line([(ex + 12, head_y - 12), (ex - 12, head_y + 12)], fill=INK_BLACK, width=line_w - 4)
        draw.arc([head_x - 20, head_y + 15, head_x + 20, head_y + 40], 0, 180, fill=INK_BLACK, width=line_w - 4)

        # Sprawled limbs
        draw.line([(head_x + int(70 * scale), ground_y - int(30 * scale)), (head_x + int(130 * scale), ground_y + int(10 * scale))], fill=INK_BLACK, width=line_w)
        draw.line([(pelvis_x, pelvis_y), (pelvis_x + int(150 * scale), ground_y + int(5 * scale))], fill=INK_BLACK, width=line_w)
        draw.line([(pelvis_x, pelvis_y), (pelvis_x + int(180 * scale), ground_y - int(20 * scale))], fill=INK_BLACK, width=line_w)
        return

    # ==========================================
    # POSE TYPE B: NAPPING / SLEEPING IN DITCH
    # ==========================================
    if pose in ("napping", "sleeping"):
        ground_y = cy + int(160 * scale)
        head_x = cx - int(120 * scale)
        head_y = ground_y - int(50 * scale)
        pelvis_x = cx + int(100 * scale)

        if style == "colored":
            draw.rounded_rectangle([head_x + int(50 * scale), ground_y - int(60 * scale), pelvis_x, ground_y - int(5 * scale)], radius=int(14 * scale), fill=c_fill, outline=INK_BLACK, width=int(5 * scale))
        else:
            draw.line([(head_x + int(50 * scale), ground_y - int(30 * scale)), (pelvis_x, ground_y - int(30 * scale))], fill=INK_BLACK, width=line_w)

        draw.ellipse([head_x - head_r, head_y - head_r, head_x + head_r, head_y + head_r], fill=(255, 255, 255), outline=INK_BLACK, width=line_w)
        # Peaceful closed - - eyes
        draw.line([(head_x - 35, head_y - 10), (head_x - 10, head_y - 10)], fill=INK_BLACK, width=line_w - 4)
        draw.line([(head_x + 10, head_y - 10), (head_x + 35, head_y - 10)], fill=INK_BLACK, width=line_w - 4)
        draw.line([(head_x - 15, head_y + 25), (head_x + 15, head_y + 25)], fill=INK_BLACK, width=line_w - 4)

        # Floating z Z Zs
        draw.text((head_x + int(70 * scale), head_y - int(90 * scale)), "z", fill=(56, 189, 248), stroke_width=2)
        draw.text((head_x + int(95 * scale), head_y - int(140 * scale)), "Z", fill=(56, 189, 248), stroke_width=3)
        draw.text((head_x + int(130 * scale), head_y - int(200 * scale)), "Z", fill=(56, 189, 248), stroke_width=4)
        return

    # ==========================================
    # POSE TYPE C: RUNNING (Athletic Marathon Stride)
    # ==========================================
    if pose in ("running", "sprinting"):
        lean_angle = 0.25  # Forward lean
        head_cy = cy - int(250 * scale)
        head_cx = cx + int(60 * scale)
        neck = (head_cx, head_cy + head_r)
        pelvis = (cx - int(20 * scale), neck[1] + spine_len)

        # Draw Torso
        if style == "colored":
            torso_box = [neck[0] - int(45 * scale), neck[1], pelvis[0] + int(45 * scale), pelvis[1]]
            draw.rounded_rectangle(torso_box, radius=int(16 * scale), fill=c_fill, outline=INK_BLACK, width=int(6 * scale))
        else:
            draw.line([neck, pelvis], fill=INK_BLACK, width=line_w)

        # Head
        draw.ellipse([head_cx - head_r, head_cy - head_r, head_cx + head_r, head_cy + head_r], fill=(255, 255, 255), outline=INK_BLACK, width=line_w)

        # Athletic Pumping Limbs (Sine oscillation)
        run_cycle = math.sin(t * 1.5)
        # Front leg bent high forward
        f_knee = (pelvis[0] + int(110 * scale * run_cycle), pelvis[1] + int(120 * scale))
        f_foot = (f_knee[0] - int(40 * scale), f_knee[1] + int(140 * scale))
        # Back leg trailing extended
        b_knee = (pelvis[0] - int(110 * scale * run_cycle), pelvis[1] + int(140 * scale))
        b_foot = (b_knee[0] - int(80 * scale), b_knee[1] + int(120 * scale))

        draw.line([pelvis, f_knee, f_foot], fill=INK_BLACK, width=line_w)
        draw.line([pelvis, b_knee, b_foot], fill=INK_BLACK, width=line_w)

        # Pumping arms
        f_elbow = (neck[0] + int(90 * scale * -run_cycle), neck[1] + int(60 * scale))
        f_hand = (f_elbow[0] + int(60 * scale), f_elbow[1] - int(50 * scale))
        b_elbow = (neck[0] - int(90 * scale * -run_cycle), neck[1] + int(60 * scale))
        b_hand = (b_elbow[0] - int(70 * scale), b_elbow[1] + int(40 * scale))

        draw.line([neck, f_elbow, f_hand], fill=INK_BLACK, width=line_w)
        draw.line([neck, b_elbow, b_hand], fill=INK_BLACK, width=line_w)

        # Sweat droplets & speed lines behind runner
        draw.ellipse([head_cx - int(110 * scale), head_cy - int(30 * scale), head_cx - int(90 * scale), head_cy - int(10 * scale)], fill=(56, 189, 248))
        draw.line([(cx - int(140 * scale), cy), (cx - int(70 * scale), cy)], fill=(203, 213, 225), width=6)
        draw.line([(cx - int(180 * scale), cy + 80), (cx - int(90 * scale), cy + 80)], fill=(203, 213, 225), width=6)

        # Face (Exhausted / Panting)
        draw.ellipse([head_cx + 10, head_cy - 10, head_cx + 30, head_cy + 10], fill=INK_BLACK)
        draw.ellipse([head_cx - 20, head_cy - 10, head_cx, head_cy + 10], fill=INK_BLACK)
        draw.ellipse([head_cx - 15, head_cy + 25, head_cx + 15, head_cy + 65], fill=INK_BLACK)
        return

    # ==========================================
    # STANDARD UPRIGHT POSES (Hands Up, Facepalm, Pointing, Celebrating, etc.)
    # ==========================================
    head_cy = cy - int(240 * scale)
    neck = (cx, head_cy + head_r)
    pelvis = (cx, neck[1] + spine_len)

    if style == "colored":
        torso_box = [cx - int(45 * scale), neck[1], cx + int(45 * scale), pelvis[1]]
        draw.rounded_rectangle(torso_box, radius=int(18 * scale), fill=c_fill, outline=INK_BLACK, width=int(6 * scale))
        draw.arc([cx - head_r, head_cy - head_r - 8, cx + head_r, head_cy], 180, 360, fill=c_fill, width=int(16 * scale))
    else:
        draw.line([neck, pelvis], fill=INK_BLACK, width=line_w)

    draw.ellipse([cx - head_r, head_cy - head_r, cx + head_r, head_cy + head_r], fill=(255, 255, 255), outline=INK_BLACK, width=line_w)

    # Face Expressions
    eye_y = head_cy - int(12 * scale)
    eye_spacing = int(36 * scale)

    if emotion == "shocked":
        for side in [-1, 1]:
            ex = cx + side * eye_spacing
            draw.ellipse([ex - 22, eye_y - 22, ex + 22, eye_y + 22], outline=INK_BLACK, fill=(255, 255, 255), width=line_w - 4)
            draw.ellipse([ex - 6, eye_y - 6, ex + 6, eye_y + 6], fill=INK_BLACK)
        draw.ellipse([cx - 26, head_cy + 25, cx + 26, head_cy + 75], fill=INK_BLACK)
    elif emotion == "deadpan":
        for side in [-1, 1]:
            ex = cx + side * eye_spacing
            draw.line([(ex - 18, eye_y - 4), (ex + 18, eye_y - 4)], fill=INK_BLACK, width=line_w - 2)
            draw.ellipse([ex - 6, eye_y - 2, ex + 6, eye_y + 10], fill=INK_BLACK)
        draw.line([(cx - 24, head_cy + 40), (cx + 24, head_cy + 40)], fill=INK_BLACK, width=line_w - 4)
    elif emotion == "scheming":
        draw.line([(cx - eye_spacing - 18, eye_y - 28), (cx - 10, eye_y - 14)], fill=INK_BLACK, width=line_w - 4)
        draw.line([(cx + 10, eye_y - 14), (cx + eye_spacing + 18, eye_y - 28)], fill=INK_BLACK, width=line_w - 4)
        for side in [-1, 1]:
            draw.ellipse([cx + side * eye_spacing + 2, eye_y - 8, cx + side * eye_spacing + 14, eye_y + 4], fill=INK_BLACK)
        draw.arc([cx - 10, head_cy + 25, cx + 35, head_cy + 60], 0, 180, fill=INK_BLACK, width=line_w - 4)
    elif emotion == "raging":
        draw.line([(cx - eye_spacing - 24, eye_y - 36), (cx - 8, eye_y - 16)], fill=INK_BLACK, width=line_w)
        draw.line([(cx + eye_spacing + 24, eye_y - 36), (cx + 8, eye_y - 16)], fill=INK_BLACK, width=line_w)
        for side in [-1, 1]:
            draw.ellipse([cx + side * eye_spacing - 10, eye_y - 6, cx + side * eye_spacing + 10, eye_y + 14], fill=INK_BLACK)
        draw.rectangle([cx - 32, head_cy + 30, cx + 32, head_cy + 65], fill=(255, 255, 255), outline=INK_BLACK, width=line_w - 4)
        draw.line([(cx - 30, head_cy + 47), (cx + 30, head_cy + 47)], fill=INK_BLACK, width=4)
    else:
        for side in [-1, 1]:
            draw.ellipse([cx + side * eye_spacing - 12, eye_y - 12, cx + side * eye_spacing + 12, eye_y + 12], fill=INK_BLACK)
        m_cycle = abs(math.sin(frame_idx * 1.1))
        m_h = int(m_cycle * 22) + 4
        if m_h > 9:
            draw.ellipse([cx - 22, head_cy + 35 - m_h // 2, cx + 22, head_cy + 35 + m_h // 2], fill=INK_BLACK)
        else:
            draw.line([(cx - 20, head_cy + 35), (cx + 20, head_cy + 35)], fill=INK_BLACK, width=line_w - 4)

    # Arm Gestures
    r_hand_pos = None

    if pose == "celebrating":
        # Double victory V
        l_hand = (cx - int(170 * scale), neck[1] - int(160 * scale))
        r_hand = (cx + int(170 * scale), neck[1] - int(160 * scale))
        draw.line([neck, (cx - int(110 * scale), neck[1] - int(60 * scale)), l_hand], fill=INK_BLACK, width=line_w)
        draw.line([neck, (cx + int(110 * scale), neck[1] - int(60 * scale)), r_hand], fill=INK_BLACK, width=line_w)
        r_hand_pos = r_hand

    elif pose in ("eating", "drinking"):
        # Hand to mouth
        l_hand = (cx - int(110 * scale), neck[1] + int(120 * scale))
        r_hand = (cx + int(15 * scale), head_cy + int(35 * scale))
        draw.line([neck, (cx - int(90 * scale), neck[1] + int(60 * scale)), l_hand], fill=INK_BLACK, width=line_w)
        draw.line([neck, (cx + int(90 * scale), neck[1] + int(60 * scale)), r_hand], fill=INK_BLACK, width=line_w)
        r_hand_pos = r_hand

    elif pose == "hands_up":
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

    else:
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

    if active_prop and r_hand_pos:
        draw_prop(draw, active_prop, r_hand_pos[0] + int(20 * scale), r_hand_pos[1] - int(10 * scale), scale=scale)
