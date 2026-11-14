"""
Vector Scene Elements Library.
Procedurally draws vehicles (vintage/modern cars, carts), nature (trees, clouds, mountains),
architecture (buildings, houses, stadium gates, fences), and dynamic shapes.
"""

from PIL import ImageDraw

def draw_vehicle(draw, vtype="car", x=540, y=1400, scale=1.0, color="#DC2626"):
    """Draws vehicles: vintage 1904 touring car, modern sedan, cart."""
    s = scale
    
    # Parse color
    if isinstance(color, str) and color.startswith("#"):
        c_body = tuple(int(color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
    else:
        c_body = color

    if vtype in ("vintage_car", "1904_car", "car"):
        # 1904 Open-top vintage touring car
        # Main chassis
        draw.rounded_rectangle([x - int(160 * s), y - int(60 * s), x + int(160 * s), y + int(20 * s)], radius=int(12 * s), fill=c_body, outline=(20, 20, 20), width=int(6 * s))
        # Cabin / Windshield frame
        draw.rectangle([x - int(60 * s), y - int(120 * s), x + int(100 * s), y - int(60 * s)], fill=(224, 242, 254), outline=(20, 20, 20), width=int(6 * s))
        # Brass headlights
        draw.ellipse([x - int(180 * s), y - int(45 * s), x - int(150 * s), y - int(15 * s)], fill=(250, 204, 21), outline=(20, 20, 20), width=int(5 * s))
        # Steering wheel
        draw.line([(x + int(40 * s), y - int(70 * s)), (x + int(20 * s), y - int(95 * s))], fill=(20, 20, 20), width=int(6 * s))
        draw.ellipse([x + int(10 * s), y - int(110 * s), x + int(35 * s), y - int(85 * s)], outline=(20, 20, 20), width=int(5 * s))
        # Wheels with spokes
        for wx in [x - int(110 * s), x + int(110 * s)]:
            draw.ellipse([wx - int(45 * s), y - int(10 * s), wx + int(45 * s), y + int(80 * s)], fill=(30, 41, 59), outline=(15, 23, 42), width=int(8 * s))
            draw.ellipse([wx - int(20 * s), y + int(15 * s), wx + int(20 * s), y + int(55 * s)], fill=(203, 213, 225), outline=(15, 23, 42), width=int(4 * s))
        # Dust puff behind car
        for dx, dy, r in [(-190, 40, 28), (-230, 25, 38), (-270, 45, 24)]:
            draw.ellipse([x + int(dx * s) - int(r * s), y + int(dy * s) - int(r * s), x + int(dx * s) + int(r * s), y + int(dy * s) + int(r * s)], fill=(226, 212, 194))

    elif vtype == "train":
        # Vintage steam train engine
        draw.rectangle([x - int(220 * s), y - int(140 * s), x + int(180 * s), y + int(20 * s)], fill=(30, 41, 59), outline=(0, 0, 0), width=int(6 * s))
        # Smokestack & Smoke
        draw.rectangle([x - int(160 * s), y - int(210 * s), x - int(110 * s), y - int(140 * s)], fill=(15, 23, 42))
        for sx, sy, sr in [(-135, -240, 30), (-165, -290, 45), (-120, -340, 60)]:
            draw.ellipse([x + int(sx * s) - int(sr * s), y + int(sy * s) - int(sr * s), x + int(sx * s) + int(sr * s), y + int(sy * s) + int(sr * s)], fill=(241, 245, 249))

def draw_nature(draw, ntype="tree", x=200, y=1400, scale=1.0):
    """Draws nature elements: oak trees, apple trees, pines, clouds, mountains."""
    s = scale

    if ntype in ("tree", "oak_tree", "apple_tree"):
        # Brown Trunk
        draw.rectangle([x - int(25 * s), y - int(240 * s), x + int(25 * s), y], fill=(120, 53, 15), outline=(20, 20, 20), width=int(6 * s))
        # Green Foliage (overlapping fluffy circles)
        foliage_color = (34, 197, 94)
        for fx, fy, fr in [(0, -280, 110), (-70, -230, 85), (70, -230, 85), (-40, -340, 75), (40, -340, 75)]:
            draw.ellipse([x + int(fx * s) - int(fr * s), y + int(fy * s) - int(fr * s), x + int(fx * s) + int(fr * s), y + int(fy * s) + int(fr * s)], fill=foliage_color, outline=(22, 101, 52), width=int(5 * s))
        # Red apples if orchard
        if ntype == "apple_tree":
            for ax, ay in [(-45, -240), (35, -260), (-15, -310), (45, -210), (-55, -290)]:
                draw.ellipse([x + int(ax * s) - int(12 * s), y + int(ay * s) - int(12 * s), x + int(ax * s) + int(12 * s), y + int(ay * s) + int(12 * s)], fill=(220, 38, 38))

    elif ntype == "pine_tree":
        # Trunk
        draw.rectangle([x - int(18 * s), y - int(120 * s), x + int(18 * s), y], fill=(69, 26, 3))
        # 3 Tiered Pine Triangles
        for tier, ty, tw, th in [(0, -100, 140, 120), (1, -180, 110, 110), (2, -260, 80, 100)]:
            points = [(x, y + int((ty - th) * s)), (x - int(tw * s), y + int(ty * s)), (x + int(tw * s), y + int(ty * s))]
            draw.polygon(points, fill=(21, 128, 61), outline=(20, 20, 20))

    elif ntype in ("cloud", "clouds"):
        # Fluffy white cartoon cloud
        for cx, cy, cr in [(0, 0, 50), (-45, 10, 38), (45, 10, 38), (-25, -20, 40), (25, -20, 40)]:
            draw.ellipse([x + int(cx * s) - int(cr * s), y + int(cy * s) - int(cr * s), x + int(cx * s) + int(cr * s), y + int(cy * s) + int(cr * s)], fill=(255, 255, 255), outline=(203, 213, 225), width=int(3 * s))

    elif ntype == "mountain":
        # Distant mountain peak
        points = [(x, y - int(380 * s)), (x - int(320 * s), y), (x + int(320 * s), y)]
        draw.polygon(points, fill=(148, 163, 184), outline=(71, 85, 105), width=int(4 * s))
        # Snow cap
        snow = [(x, y - int(380 * s)), (x - int(90 * s), y - int(260 * s)), (x, y - int(240 * s)), (x + int(90 * s), y - int(260 * s))]
        draw.polygon(snow, fill=(255, 255, 255))

def draw_architecture(draw, btype="city_building", x=300, y=1400, scale=1.0, color="#64748B"):
    """Draws architecture: skyscraper/buildings, houses, stadium gates, finish banners."""
    s = scale

    if btype in ("building", "city_building"):
        # Multi-story building with illuminated windows
        bx1, by1 = x - int(120 * s), y - int(550 * s)
        bx2, by2 = x + int(120 * s), y
        draw.rectangle([bx1, by1, bx2, by2], fill=(71, 85, 105), outline=(15, 23, 42), width=int(6 * s))
        # Windows grid
        for row in range(5):
            for col in range(3):
                wx = bx1 + int(25 * s) + (col * int(70 * s))
                wy = by1 + int(40 * s) + (row * int(95 * s))
                draw.rectangle([wx, wy, wx + int(45 * s), wy + int(60 * s)], fill=(254, 240, 138), outline=(30, 41, 59), width=int(3 * s))

    elif btype in ("finish_banner", "banner"):
        # Olympic finish line ribbon / banner across track
        # Poles
        draw.line([(x - int(260 * s), y - int(280 * s)), (x - int(260 * s), y)], fill=(30, 41, 59), width=int(10 * s))
        draw.line([(x + int(260 * s), y - int(280 * s)), (x + int(260 * s), y)], fill=(30, 41, 59), width=int(10 * s))
        # Red ribbon
        draw.rectangle([x - int(260 * s), y - int(260 * s), x + int(260 * s), y - int(210 * s)], fill=(220, 38, 38), outline=(15, 23, 42), width=int(4 * s))

    elif btype == "fence":
        # Wooden picket fence
        for fx in range(x - int(200 * s), x + int(200 * s), int(40 * s)):
            draw.rectangle([fx, y - int(90 * s), fx + int(25 * s), y], fill=(241, 245, 249), outline=(100, 116, 139), width=int(3 * s))
        draw.line([(x - int(200 * s), y - int(65 * s)), (x + int(200 * s), y - int(65 * s))], fill=(100, 116, 139), width=int(5 * s))
