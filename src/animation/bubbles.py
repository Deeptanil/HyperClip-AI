"""
Speech and Thought Bubbles System (Inspired by Yash-Kavaiya/manim-video-generator-actor).
Renders vector dialogue bubbles with directional tails pointing directly to speaking actors.
"""

from PIL import ImageDraw, ImageFont

INK_BLACK = (20, 20, 24)

def draw_speech_bubble(draw, text, target_mouth_xy, bubble_xy, width=280, height=110, bubble_type="speech"):
    """
    Renders a speech or thought bubble with text and a tail pointing to target_mouth_xy.
    """
    bx, by = bubble_xy
    mx, my = target_mouth_xy

    # 1. Bubble Body
    box = [bx - width // 2, by - height // 2, bx + width // 2, by + height // 2]
    
    if bubble_type == "thought":
        # Thought Cloud: 3 connected ellipses
        draw.ellipse(box, fill=(255, 255, 255), outline=INK_BLACK, width=4)
        # Small thought bubbles leading to head
        step_x = (mx - bx) / 4
        step_y = (my - by) / 4
        for i in range(1, 4):
            dot_x = int(bx + step_x * i)
            dot_y = int(by + step_y * i)
            r = int(5 + i * 3)
            draw.ellipse([dot_x - r, dot_y - r, dot_x + r, dot_y + r], fill=(255, 255, 255), outline=INK_BLACK, width=3)
    else:
        # Standard Speech Bubble (Rounded rectangle)
        draw.rounded_rectangle(box, radius=18, fill=(255, 255, 255), outline=INK_BLACK, width=4)
        
        # Directional Tail pointing to mouth
        tail_root_x = bx + (25 if mx > bx else -25)
        tail_root_y = by + height // 2 - 2
        tail_poly = [
            (tail_root_x - 14, tail_root_y),
            (tail_root_x + 14, tail_root_y),
            (mx, my)
        ]
        draw.polygon(tail_poly, fill=(255, 255, 255))
        draw.line([(tail_root_x - 14, tail_root_y), (mx, my), (tail_root_x + 14, tail_root_y)], fill=INK_BLACK, width=4)

    # 2. Text Inside Bubble
    try:
        font = ImageFont.truetype("arialbd.ttf", 26)
    except Exception:
        font = ImageFont.load_default()

    # Wrap text into 2-3 lines if long
    words = text.split()
    lines = []
    curr = []
    for w in words:
        if len(" ".join(curr + [w])) <= 16:
            curr.append(w)
        else:
            lines.append(" ".join(curr))
            curr = [w]
    if curr:
        lines.append(" ".join(curr))

    total_text_h = len(lines) * 32
    start_ty = by - total_text_h // 2
    for i, line in enumerate(lines):
        # Center line
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        tx = bx - line_w // 2
        ty = start_ty + (i * 32)
        draw.text((tx, ty), line, fill=INK_BLACK, font=font)
