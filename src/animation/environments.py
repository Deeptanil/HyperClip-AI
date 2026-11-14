"""
Procedural Vector Environments (9:16 Vertical Canvas).
Renders stylized backgrounds for historical, mythological, and urban settings.
"""

from PIL import ImageDraw

WIDTH = 1080
HEIGHT = 1920

def draw_environment(draw, env_type="default", width=WIDTH, height=HEIGHT):
    """Renders environment layer onto the image canvas."""
    
    if env_type == "palace":
        # Throne room / Castle pillars
        # Floor
        draw.rectangle([0, height - 450, width, height], fill=(180, 160, 140))
        # Red Carpet
        draw.rectangle([width // 2 - 220, height - 450, width // 2 + 220, height], fill=(185, 28, 28))
        # Stone Pillars
        for px in [120, width - 120]:
            draw.rectangle([px - 45, 0, px + 45, height - 450], fill=(210, 200, 190), outline=(50, 50, 50), width=6)
            # Pillar Capitals
            draw.rectangle([px - 65, 0, px + 65, 80], fill=(190, 180, 170), outline=(50, 50, 50), width=6)
            draw.rectangle([px - 65, height - 510, px + 65, height - 450], fill=(190, 180, 170), outline=(50, 50, 50), width=6)
        # Arched palace window in center
        cx = width // 2
        draw.arc([cx - 160, 220, cx + 160, 540], 180, 360, fill=(50, 50, 50), width=8)
        draw.rectangle([cx - 160, 380, cx + 160, 750], fill=(191, 219, 254), outline=(50, 50, 50), width=8)

    elif env_type in ("desert", "dust_road"):
        # Arid desert / marathon dirt road
        # Sky gradient / Warm sun
        draw.ellipse([width // 2 - 90, 240, width // 2 + 90, 420], fill=(251, 191, 36))
        # Distant dunes
        draw.chord([0, 600, width, 1200], 0, 180, fill=(245, 158, 11))
        # Ground
        draw.rectangle([0, height - 600, width, height], fill=(217, 119, 6))
        # Dirt road
        draw.polygon([(width // 2 - 80, height - 600), (width // 2 + 80, height - 600), (width, height), (0, height)], fill=(180, 83, 9))

    elif env_type in ("stadium", "finish_line", "podium"):
        # Olympic track
        # Blue sky
        draw.rectangle([0, 0, width, height - 600], fill=(224, 242, 254))
        # Bleachers
        for step in range(5):
            sy = height - 900 + (step * 60)
            draw.rectangle([0, sy, width, sy + 60], fill=(148, 163, 184), outline=(71, 85, 105), width=4)
        # Running track
        draw.rectangle([0, height - 600, width, height], fill=(185, 28, 28))
        # White lane lines
        for ly in [height - 400, height - 200]:
            draw.line([(0, ly), (width, ly)], fill=(255, 255, 255), width=12)

    elif env_type in ("banquet", "tavern"):
        # Medieval tavern banquet
        # Dark wood walls
        draw.rectangle([0, 0, width, height - 400], fill=(68, 64, 60))
        # Floor
        draw.rectangle([0, height - 400, width, height], fill=(41, 37, 36))
        # Hanging torch / chandelier
        cx = width // 2
        draw.line([(cx, 0), (cx, 260)], fill=(20, 20, 20), width=8)
        draw.ellipse([cx - 40, 260, cx + 40, 310], fill=(245, 158, 11))
        # Large wooden table
        draw.rectangle([100, height - 520, width - 100, height - 380], fill=(120, 53, 15), outline=(20, 20, 20), width=8)

    elif env_type in ("hotel_suite", "paris_street", "eiffel_tower"):
        # Elegant 1920s interior with Paris window
        # Floor
        draw.rectangle([0, height - 450, width, height], fill=(203, 213, 225))
        # Wallpaper
        draw.rectangle([0, 0, width, height - 450], fill=(241, 245, 249))
        # Large window showing Eiffel Tower silhouette
        wx1, wy1, wx2, wy2 = width // 2 - 180, 280, width // 2 + 180, 850
        draw.rectangle([wx1, wy1, wx2, wy2], fill=(186, 230, 253), outline=(30, 41, 59), width=8)
        # Eiffel Tower silhouette in window
        cx = width // 2
        draw.polygon([(cx, wy1 + 100), (cx - 70, wy2), (cx + 70, wy2)], fill=(100, 116, 139))
        draw.line([(cx - 45, wy2 - 160), (cx + 45, wy2 - 160)], fill=(71, 85, 105), width=6)
        draw.line([(cx - 30, wy2 - 280), (cx + 30, wy2 - 280)], fill=(71, 85, 105), width=6)

    else:
        # Default clean minimalist warm paper with subtle floor line
        draw.rectangle([0, 0, width, height], fill=(250, 248, 244))
        draw.line([(0, height - 400), (width, height - 400)], fill=(215, 212, 205), width=6)
