"""
Professional 2D Stick-Figure Skeletal Kinematics Engine.
Ensures 100% continuous joint connectivity (no broken bodies, floating spines, or disconnected limbs).
Supports smooth running, jumping, athletic strides, and emotional gestures.
"""

import math
import random
from PIL import Image, ImageDraw
from .props import draw_prop

INK_BLACK = (20, 20, 24)

def draw_capsule_line(draw, p1, p2, width=14, color=INK_BLACK):
    """Draws a thick line with perfectly rounded joint caps so limbs never look broken."""
    draw.line([p1, p2], fill=color, width=width)
    r = width // 2
    draw.ellipse([p1[0] - r, p1[1] - r, p1[0] + r, p1[1] + r], fill=color)
    draw.ellipse([p2[0] - r, p2[1] - r, p2[0] + r, p2[1] + r], fill=color)

def draw_limb_2segment(draw, joint_root, joint_mid, joint_end, width=14, color=INK_BLACK):
    """Draws a 2-segment limb (e.g. Shoulder -> Elbow -> Hand, or Hip -> Knee -> Foot)."""
    draw_capsule_line(draw, joint_root, joint_mid, width=width, color=color)
    draw_capsule_line(draw, joint_mid, joint_end, width=width, color=color)

def draw_character(draw, cx, cy, char_config, frame_idx=0, scale=1.0, active_prop=None):
    """
    Renders an anatomically sound, connected stick figure.
    Guarantees:
      - Head sits on neck
      - Neck connects to spine and shoulders
      - Spine connects to pelvis
      - Both legs branch from pelvis
      - Both arms branch from shoulders
    """
    style = char_config.get("style", "colored")
    color = char_config.get("color", "#2563EB")
    emotion = char_config.get("emotion", "talking")
    pose = char_config.get("pose", "stand")

    if isinstance(color, str) and color.startswith("#"):
        c_fill = tuple(int(color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
    else:
        c_fill = color

    line_w = int(14 * scale)
    head_r = int(68 * scale)
    torso_len = int(220 * scale)
    shoulder_w = int(45 * scale)

    # Micro-jitter for hand-drawn boiling (applied consistently to whole body root)
    random.seed(frame_idx * 19 + hash(char_config.get("id", "char")))
    jx = random.randint(-1, 1)
    jy = random.randint(-1, 1)
    cx += jx
    cy += jy

    t = frame_idx * 0.9

    # ========================================================
    # 1. ATHLETIC RUNNING STRIDE (Connected Kinematics)
    # ========================================================
    if pose in ("running", "sprinting"):
        lean_angle = 0.28  # Forward athletic angle
        
        # Center of mass
        pelvis_x = cx
        pelvis_y = cy + int(40 * scale)

        # Neck position determined by lean angle from pelvis
        neck_x = pelvis_x + int(math.sin(lean_angle) * torso_len)
        neck_y = pelvis_y - int(math.cos(lean_angle) * torso_len)

        # Head sits directly atop the neck
        head_cx = neck_x + int(math.sin(lean_angle) * head_r)
        head_cy = neck_y - int(math.cos(lean_angle) * head_r)

        # Shoulders (25% down the spine from neck)
        shoulder_root_x = neck_x - int(math.sin(lean_angle) * 35 * scale)
        shoulder_root_y = neck_y + int(math.cos(lean_angle) * 35 * scale)

        # Draw Torso (Continuous Spine / Shirt)
        if style == "colored":
            # Connected sporty colored athletic shirt
            torso_poly = [
                (neck_x - shoulder_w, neck_y),
                (neck_x + shoulder_w, neck_y),
                (pelvis_x + int(shoulder_w * 0.8), pelvis_y),
                (pelvis_x - int(shoulder_w * 0.8), pelvis_y)
            ]
            draw.polygon(torso_poly, fill=c_fill, outline=INK_BLACK)
            draw_capsule_line(draw, (neck_x, neck_y), (pelvis_x, pelvis_y), width=line_w - 4, color=c_fill)
        else:
            draw_capsule_line(draw, (neck_x, neck_y), (pelvis_x, pelvis_y), width=line_w, color=INK_BLACK)

        # Head Circle
        draw.ellipse([head_cx - head_r, head_cy - head_r, head_cx + head_r, head_cy + head_r], fill=(255, 255, 255), outline=INK_BLACK, width=line_w)

        # Headband / Cap if colored
        if style == "colored":
            draw.arc([head_cx - head_r, head_cy - head_r - 4, head_cx + head_r, head_cy], 180, 360, fill=c_fill, width=int(14 * scale))

        # Legs (Both firmly rooted at pelvis_x, pelvis_y)
        stride_phase = math.sin(t * 1.6)
        
        # Front Leg (Thigh -> Knee -> Shin -> Foot)
        f_knee_x = pelvis_x + int((100 * stride_phase + 30) * scale)
        f_knee_y = pelvis_y + int(110 * scale)
        f_foot_x = f_knee_x + int(40 * scale)
        f_foot_y = f_knee_y + int(110 * scale)
        draw_limb_2segment(draw, (pelvis_x, pelvis_y), (f_knee_x, f_knee_y), (f_foot_x, f_foot_y), width=line_w)
        # Foot stroke
        draw_capsule_line(draw, (f_foot_x - int(10 * scale), f_foot_y), (f_foot_x + int(25 * scale), f_foot_y), width=line_w)

        # Back Leg (Thigh -> Knee -> Shin -> Foot)
        b_knee_x = pelvis_x - int((100 * stride_phase - 20) * scale)
        b_knee_y = pelvis_y + int(120 * scale)
        b_foot_x = b_knee_x - int(50 * scale)
        b_foot_y = b_knee_y + int(100 * scale)
        draw_limb_2segment(draw, (pelvis_x, pelvis_y), (b_knee_x, b_knee_y), (b_foot_x, b_foot_y), width=line_w)
        draw_capsule_line(draw, (b_foot_x - int(25 * scale), b_foot_y), (b_foot_x + int(10 * scale), b_foot_y), width=line_w)

        # Arms (Rooted at shoulder_root)
        f_elbow_x = shoulder_root_x - int(80 * stride_phase * scale)
        f_elbow_y = shoulder_root_y + int(60 * scale)
        f_hand_x = f_elbow_x + int(65 * scale)
        f_hand_y = f_elbow_y - int(45 * scale)
        draw_limb_2segment(draw, (shoulder_root_x, shoulder_root_y), (f_elbow_x, f_elbow_y), (f_hand_x, f_hand_y), width=line_w)

        b_elbow_x = shoulder_root_x + int(80 * stride_phase * scale)
        b_elbow_y = shoulder_root_y + int(60 * scale)
        b_hand_x = b_elbow_x - int(55 * scale)
        b_hand_y = b_elbow_y - int(30 * scale)
        draw_limb_2segment(draw, (shoulder_root_x, shoulder_root_y), (b_elbow_x, b_elbow_y), (b_hand_x, b_hand_y), width=line_w)

        # Expressive Face (Panting & Determined)
        eye_y = head_cy - int(8 * scale)
        draw.ellipse([head_cx + int(10 * scale), eye_y - 10, head_cx + int(28 * scale), eye_y + 8], fill=INK_BLACK)
        draw.ellipse([head_cx - int(24 * scale), eye_y - 10, head_cx - int(6 * scale), eye_y + 8], fill=INK_BLACK)
        # Panting mouth
        draw.ellipse([head_cx - int(12 * scale), head_cy + int(18 * scale), head_cx + int(16 * scale), head_cy + int(50 * scale)], fill=INK_BLACK)

        # Sweat bead flying backwards
        draw.ellipse([head_cx - int(95 * scale), head_cy - int(20 * scale), head_cx - int(78 * scale), head_cy - int(3 * scale)], fill=(56, 189, 248))
        return

    # ========================================================
    # 2. COLLAPSED ON GROUND (Continuous Lying Skeleton)
    # ========================================================
    if pose in ("collapsed", "fainted"):
        ground_y = cy + int(180 * scale)
        head_cx = cx - int(180 * scale)
        head_cy = ground_y - int(40 * scale)
        neck = (head_cx + head_r, head_cy)
        pelvis = (cx + int(90 * scale), ground_y - int(30 * scale))

        if style == "colored":
            draw.rounded_rectangle([neck[0] - 10, ground_y - int(60 * scale), pelvis[0] + 10, ground_y - 5], radius=12, fill=c_fill, outline=INK_BLACK, width=int(5 * scale))
        else:
            draw_capsule_line(draw, neck, pelvis, width=line_w)

        draw.ellipse([head_cx - head_r, head_cy - head_r, head_cx + head_r, head_cy + head_r], fill=(255, 255, 255), outline=INK_BLACK, width=line_w)

        # X X Eyes
        for ex in [head_cx - 20, head_cx + 18]:
            draw.line([(ex - 10, head_cy - 10), (ex + 10, head_cy + 10)], fill=INK_BLACK, width=line_w - 4)
            draw.line([(ex + 10, head_cy - 10), (ex - 10, head_cy + 10)], fill=INK_BLACK, width=line_w - 4)

        # Limbs sprawled
        draw_limb_2segment(draw, neck, (neck[0] + int(60 * scale), ground_y + int(5 * scale)), (neck[0] + int(120 * scale), ground_y + int(15 * scale)), width=line_w)
        draw_limb_2segment(draw, pelvis, (pelvis[0] + int(80 * scale), ground_y + int(10 * scale)), (pelvis[0] + int(160 * scale), ground_y + int(15 * scale)), width=line_w)
        return

    # ========================================================
    # 3. NAPPING / SLEEPING
    # ========================================================
    if pose in ("napping", "sleeping"):
        ground_y = cy + int(180 * scale)
        head_cx = cx - int(140 * scale)
        head_cy = ground_y - int(50 * scale)
        neck = (head_cx + head_r, head_cy)
        pelvis = (cx + int(80 * scale), ground_y - int(35 * scale))

        if style == "colored":
            draw.rounded_rectangle([neck[0] - 10, ground_y - int(60 * scale), pelvis[0], ground_y - 10], radius=14, fill=c_fill, outline=INK_BLACK, width=int(5 * scale))
        else:
            draw_capsule_line(draw, neck, pelvis, width=line_w)

        draw.ellipse([head_cx - head_r, head_cy - head_r, head_cx + head_r, head_cy + head_r], fill=(255, 255, 255), outline=INK_BLACK, width=line_w)
        draw.line([(head_cx - 30, head_cy - 8), (head_cx - 8, head_cy - 8)], fill=INK_BLACK, width=line_w - 4)
        draw.line([(head_cx + 8, head_cy - 8), (head_cx + 30, head_cy - 8)], fill=INK_BLACK, width=line_w - 4)

        # ZZZ
        draw.text((head_cx + int(60 * scale), head_cy - int(80 * scale)), "z", fill=(56, 189, 248), stroke_width=2)
        draw.text((head_cx + int(90 * scale), head_cy - int(130 * scale)), "Z", fill=(56, 189, 248), stroke_width=3)
        draw.text((head_cx + int(125 * scale), head_cy - int(185 * scale)), "Z", fill=(56, 189, 248), stroke_width=4)
        return

    # ========================================================
    # 4. STANDARD UPRIGHT BODY (Continuous Spine & Joints)
    # ========================================================
    head_cy = cy - int(240 * scale)
    neck = (cx, head_cy + head_r)
    pelvis = (cx, neck[1] + torso_len)
    shoulders = (cx, neck[1] + int(35 * scale))

    # Torso
    if style == "colored":
        draw.rounded_rectangle([cx - shoulder_w, neck[1], cx + shoulder_w, pelvis[1]], radius=int(16 * scale), fill=c_fill, outline=INK_BLACK, width=int(5 * scale))
        draw.arc([cx - head_r, head_cy - head_r - 4, cx + head_r, head_cy], 180, 360, fill=c_fill, width=int(14 * scale))
    else:
        draw_capsule_line(draw, neck, pelvis, width=line_w)

    # Head
    draw.ellipse([cx - head_r, head_cy - head_r, cx + head_r, head_cy + head_r], fill=(255, 255, 255), outline=INK_BLACK, width=line_w)

    # Face Features
    eye_y = head_cy - int(12 * scale)
    eye_spacing = int(32 * scale)

    if emotion == "shocked":
        for side in [-1, 1]:
            ex = cx + side * eye_spacing
            draw.ellipse([ex - 20, eye_y - 20, ex + 20, eye_y + 20], outline=INK_BLACK, fill=(255, 255, 255), width=line_w - 4)
            draw.ellipse([ex - 6, eye_y - 6, ex + 6, eye_y + 6], fill=INK_BLACK)
        draw.ellipse([cx - 24, head_cy + 22, cx + 24, head_cy + 68], fill=INK_BLACK)
    elif emotion == "deadpan":
        for side in [-1, 1]:
            ex = cx + side * eye_spacing
            draw.line([(ex - 16, eye_y - 4), (ex + 16, eye_y - 4)], fill=INK_BLACK, width=line_w - 2)
            draw.ellipse([ex - 5, eye_y - 2, ex + 5, eye_y + 8], fill=INK_BLACK)
        draw.line([(cx - 22, head_cy + 36), (cx + 22, head_cy + 36)], fill=INK_BLACK, width=line_w - 4)
    elif emotion == "scheming":
        draw.line([(cx - eye_spacing - 16, eye_y - 24), (cx - 8, eye_y - 12)], fill=INK_BLACK, width=line_w - 4)
        draw.line([(cx + 8, eye_y - 12), (cx + eye_spacing + 16, eye_y - 24)], fill=INK_BLACK, width=line_w - 4)
        for side in [-1, 1]:
            draw.ellipse([cx + side * eye_spacing + 2, eye_y - 6, cx + side * eye_spacing + 12, eye_y + 4], fill=INK_BLACK)
        draw.arc([cx - 8, head_cy + 22, cx + 32, head_cy + 52], 0, 180, fill=INK_BLACK, width=line_w - 4)
    else:
        for side in [-1, 1]:
            draw.ellipse([cx + side * eye_spacing - 10, eye_y - 10, cx + side * eye_spacing + 10, eye_y + 10], fill=INK_BLACK)
        m_cycle = abs(math.sin(frame_idx * 1.1))
        m_h = int(m_cycle * 20) + 4
        if m_h > 8:
            draw.ellipse([cx - 18, head_cy + 32 - m_h // 2, cx + 18, head_cy + 32 + m_h // 2], fill=INK_BLACK)
        else:
            draw.line([(cx - 18, head_cy + 32), (cx + 18, head_cy + 32)], fill=INK_BLACK, width=line_w - 4)

    # Arm Gestures (Branching directly from Shoulders)
    r_hand_pos = None

    if pose == "celebrating":
        l_hand = (cx - int(150 * scale), neck[1] - int(140 * scale))
        r_hand = (cx + int(150 * scale), neck[1] - int(140 * scale))
        draw_limb_2segment(draw, shoulders, (cx - int(95 * scale), neck[1] - int(45 * scale)), l_hand, width=line_w)
        draw_limb_2segment(draw, shoulders, (cx + int(95 * scale), neck[1] - int(45 * scale)), r_hand, width=line_w)
        r_hand_pos = r_hand
    elif pose in ("eating", "drinking"):
        l_hand = (cx - int(100 * scale), neck[1] + int(110 * scale))
        r_hand = (cx + int(15 * scale), head_cy + int(30 * scale))
        draw_limb_2segment(draw, shoulders, (cx - int(80 * scale), neck[1] + int(60 * scale)), l_hand, width=line_w)
        draw_limb_2segment(draw, shoulders, (cx + int(80 * scale), neck[1] + int(50 * scale)), r_hand, width=line_w)
        r_hand_pos = r_hand
    elif pose == "hands_up":
        l_hand = (cx - int(150 * scale), neck[1] - int(100 * scale) + int(math.sin(t) * 12))
        r_hand = (cx + int(150 * scale), neck[1] - int(100 * scale) - int(math.sin(t) * 12))
        draw_limb_2segment(draw, shoulders, (cx - int(100 * scale), neck[1] - int(15 * scale)), l_hand, width=line_w)
        draw_limb_2segment(draw, shoulders, (cx + int(100 * scale), neck[1] - int(15 * scale)), r_hand, width=line_w)
        r_hand_pos = r_hand
    elif pose == "facepalm":
        l_hand = (cx - int(120 * scale), neck[1] + int(130 * scale))
        r_hand = (cx + int(20 * scale), head_cy + int(15 * scale))
        draw_limb_2segment(draw, shoulders, (cx - int(90 * scale), neck[1] + int(60 * scale)), l_hand, width=line_w)
        draw_limb_2segment(draw, shoulders, (cx + int(90 * scale), neck[1] + int(35 * scale)), r_hand, width=line_w)
    elif pose == "pointing":
        l_hand = (cx - int(110 * scale), neck[1] + int(110 * scale))
        r_hand = (cx + int(220 * scale), neck[1] - int(15 * scale))
        draw_limb_2segment(draw, shoulders, (cx - int(80 * scale), neck[1] + int(55 * scale)), l_hand, width=line_w)
        draw_limb_2segment(draw, shoulders, (cx + int(110 * scale), neck[1] + int(10 * scale)), r_hand, width=line_w)
        r_hand_pos = r_hand
    else:
        l_hand = (cx - int(130 * scale), neck[1] + int(140 * scale) + int(math.sin(t) * 12))
        r_hand = (cx + int(130 * scale), neck[1] + int(140 * scale) - int(math.sin(t) * 12))
        draw_limb_2segment(draw, shoulders, (cx - int(90 * scale), neck[1] + int(65 * scale)), l_hand, width=line_w)
        draw_limb_2segment(draw, shoulders, (cx + int(90 * scale), neck[1] + int(65 * scale)), r_hand, width=line_w)
        r_hand_pos = r_hand

    # Legs (Rooted firmly at Pelvis with shoes)
    leg_len = int(280 * scale)
    l_foot = (cx - int(75 * scale), pelvis[1] + leg_len)
    r_foot = (cx + int(75 * scale), pelvis[1] + leg_len)
    
    # Left & Right legs
    draw_limb_2segment(draw, pelvis, (cx - int(55 * scale), pelvis[1] + int(140 * scale)), l_foot, width=line_w)
    draw_capsule_line(draw, (l_foot[0] - int(25 * scale), l_foot[1]), (l_foot[0] + int(10 * scale), l_foot[1]), width=line_w)
    
    draw_limb_2segment(draw, pelvis, (cx + int(55 * scale), pelvis[1] + int(140 * scale)), r_foot, width=line_w)
    draw_capsule_line(draw, (r_foot[0] - int(10 * scale), r_foot[1]), (r_foot[0] + int(25 * scale), r_foot[1]), width=line_w)

    if active_prop and r_hand_pos:
        draw_prop(draw, active_prop, r_hand_pos[0] + int(18 * scale), r_hand_pos[1] - int(10 * scale), scale=scale)
