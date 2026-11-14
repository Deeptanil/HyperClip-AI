"""
Procedural Vector Props System.
Draws dynamic story props that stick figures hold and interact with.
"""

from PIL import ImageDraw

def draw_prop(draw, prop_name, x, y, scale=1.0):
    """Draws a prop centered at coordinate (x, y)."""
    s = scale

    if prop_name == "hammer":
        # Mjolnir: Heavy stone hammerhead + brown handle
        draw.line([(x, y + int(35 * s)), (x, y - int(35 * s))], fill=(120, 53, 15), width=int(14 * s))
        # Stone block
        bx1, by1 = x - int(45 * s), y - int(65 * s)
        bx2, by2 = x + int(45 * s), y - int(25 * s)
        draw.rectangle([bx1, by1, bx2, by2], fill=(148, 163, 184), outline=(15, 23, 42), width=int(6 * s))

    elif prop_name == "crown":
        # Golden royal crown
        points = [
            (x - int(40 * s), y + int(15 * s)),
            (x - int(40 * s), y - int(25 * s)),
            (x - int(20 * s), y - int(5 * s)),
            (x, y - int(35 * s)),
            (x + int(20 * s), y - int(5 * s)),
            (x + int(40 * s), y - int(25 * s)),
            (x + int(40 * s), y + int(15 * s))
        ]
        draw.polygon(points, fill=(234, 179, 8), outline=(15, 23, 42))

    elif prop_name == "briefcase":
        # Brown leather briefcase
        bx1, by1 = x - int(45 * s), y - int(30 * s)
        bx2, by2 = x + int(45 * s), y + int(30 * s)
        draw.rectangle([bx1, by1, bx2, by2], fill=(146, 64, 14), outline=(15, 23, 42), width=int(6 * s))
        # Handle
        draw.arc([x - int(18 * s), by1 - int(18 * s), x + int(18 * s), by1 + int(10 * s)], 180, 360, fill=(15, 23, 42), width=int(6 * s))

    elif prop_name in ("cash_bag", "money"):
        # Green money sack with $ sign
        draw.ellipse([x - int(40 * s), y - int(40 * s), x + int(40 * s), y + int(40 * s)], fill=(34, 197, 94), outline=(15, 23, 42), width=int(6 * s))
        draw.polygon([(x - int(20 * s), y - int(40 * s)), (x, y - int(60 * s)), (x + int(20 * s), y - int(40 * s))], fill=(34, 197, 94))
        # Dollar sign
        draw.line([(x, y - int(20 * s)), (x, y + int(20 * s))], fill=(15, 23, 42), width=int(4 * s))

    elif prop_name == "newspaper":
        # Vintage newspaper
        draw.rectangle([x - int(40 * s), y - int(50 * s), x + int(40 * s), y + int(50 * s)], fill=(241, 245, 249), outline=(15, 23, 42), width=int(5 * s))
        # Text lines
        for offset_y in [-25, -10, 5, 20, 35]:
            draw.line([(x - int(28 * s), y + int(offset_y * s)), (x + int(28 * s), y + int(offset_y * s))], fill=(100, 116, 139), width=int(3 * s))

    elif prop_name == "meat":
        # Roasted cartoon drumstick
        draw.ellipse([x - int(25 * s), y - int(20 * s), x + int(35 * s), y + int(20 * s)], fill=(180, 83, 9), outline=(15, 23, 42), width=int(5 * s))
        # Bone
        draw.line([(x - int(20 * s), y), (x - int(45 * s), y)], fill=(255, 255, 255), width=int(8 * s))

    elif prop_name in ("trophy", "medal"):
        # Golden first place trophy
        draw.polygon([(x - int(30 * s), y - int(40 * s)), (x + int(30 * s), y - int(40 * s)), (x, y + int(10 * s))], fill=(250, 204, 21), outline=(15, 23, 42), width=int(5 * s))
        draw.rectangle([x - int(25 * s), y + int(20 * s), x + int(25 * s), y + int(35 * s)], fill=(100, 116, 139), outline=(15, 23, 42), width=int(4 * s))

    elif prop_name == "apple":
        # Red apple
        draw.ellipse([x - int(22 * s), y - int(22 * s), x + int(22 * s), y + int(22 * s)], fill=(220, 38, 38), outline=(15, 23, 42), width=int(4 * s))
        # Green leaf
        draw.line([(x, y - int(22 * s)), (x + int(10 * s), y - int(35 * s))], fill=(34, 197, 94), width=int(4 * s))
