"""
Storyboard & Visual Director Engine.
Converts any narrative story text into a fully choreographed visual script:
- Environments & color palettes
- Scene elements: cars, trains, trees, clouds, buildings, fences
- Multiple stick figures with specialized poses (running, collapsed, napping, celebrating, pointing)
- Props, camera movements, and timed sound effects
"""

import json

def convert_story_to_visual_script(story_text, title="Generated Story"):
    """
    Parses narrative paragraphs/sentences into structured visual scenes
    with environments, objects, vehicles, and multi-character choreography.
    """
    paragraphs = [p.strip() for p in story_text.split("\n") if p.strip()]
    if not paragraphs:
        paragraphs = [story_text]

    scenes = []
    
    for idx, p in enumerate(paragraphs):
        p_lower = p.lower()
        
        # 1. Infer Environment
        if any(w in p_lower for w in ["stadium", "marathon", "race", "track", "olympic"]):
            env = "stadium"
        elif any(w in p_lower for w in ["desert", "dust", "dirt road", "road", "heat"]):
            env = "dust_road"
        elif any(w in p_lower for w in ["orchard", "apple", "farm", "forest"]):
            env = "orchard"
        elif any(w in p_lower for w in ["finish", "won", "medal", "line"]):
            env = "finish_line"
        elif any(w in p_lower for w in ["palace", "castle", "king", "throne"]):
            env = "palace"
        elif any(w in p_lower for w in ["paris", "city", "street", "building"]):
            env = "paris_street"
        elif any(w in p_lower for w in ["hotel", "suite", "meeting", "office"]):
            env = "hotel_suite"
        else:
            env = "default"

        # 2. Infer Elements (Vehicles, Trees, Architecture)
        elements = []
        if any(w in p_lower for w in ["car", "drive", "drove", "vehicle"]):
            elements.append({"type": "vehicle", "name": "vintage_car", "x": 800, "y": 1420, "scale": 1.05, "color": "#991B1B"})
        if any(w in p_lower for w in ["train", "rail"]):
            elements.append({"type": "vehicle", "name": "train", "x": 540, "y": 1400, "scale": 1.0})
        if any(w in p_lower for w in ["apple", "tree", "orchard"]):
            elements.append({"type": "nature", "name": "apple_tree", "x": 220, "y": 1450, "scale": 0.95})
            elements.append({"type": "nature", "name": "apple_tree", "x": 860, "y": 1450, "scale": 0.95})
        if any(w in p_lower for w in ["building", "city", "tower"]):
            elements.append({"type": "architecture", "name": "city_building", "x": 180, "y": 1450, "scale": 0.85})
        if any(w in p_lower for w in ["cloud", "sky", "sun"]):
            elements.append({"type": "nature", "name": "clouds", "x": 400, "y": 280, "scale": 0.8})

        # 3. Infer Characters & Specialized Poses
        chars = []
        if any(w in p_lower for w in ["run", "running", "marathon", "sprint"]):
            chars.append({"id": "runner_1", "style": "colored", "color": "#2563EB", "emotion": "talking", "pose": "running", "x": 400})
            chars.append({"id": "runner_2", "style": "bw", "emotion": "shocked", "pose": "running", "x": 700})
        elif any(w in p_lower for w in ["collapsed", "vomit", "fainted", "blood", "passed out"]):
            chars.append({"id": "collapsed_runner", "style": "bw", "emotion": "deadpan", "pose": "collapsed", "x": 380})
        elif any(w in p_lower for w in ["nap", "napping", "sleep", "sleeping", "ditch"]):
            chars.append({"id": "sleeper", "style": "colored", "color": "#0284C7", "emotion": "deadpan", "pose": "napping", "x": 540})
        elif any(w in p_lower for w in ["won", "celebrat", "victory", "triumph"]):
            chars.append({"id": "winner", "style": "colored", "color": "#16A34A", "emotion": "laughing", "pose": "celebrating", "x": 540})
        elif any(w in p_lower for w in ["eat", "ate", "hungry", "snack"]):
            chars.append({"id": "eater", "style": "colored", "color": "#0284C7", "emotion": "talking", "pose": "eating", "x": 540})
        else:
            chars.append({"id": "narrator", "style": "colored", "color": "#DC2626", "emotion": "talking", "pose": "hands_up", "x": 540})

        # 4. Infer Props
        props = []
        if "apple" in p_lower:
            props.append("apple")
        if "trophy" in p_lower or "won" in p_lower:
            props.append("trophy")
        if "medal" in p_lower:
            props.append("medal")
        if "hammer" in p_lower:
            props.append("hammer")
        if "cash" in p_lower or "money" in p_lower or "dollar" in p_lower:
            props.append("cash_bag")
        if "newspaper" in p_lower:
            props.append("newspaper")

        # 5. Camera & SFX
        cam = "zoom_in" if (idx % 2 == 1) else "normal"
        sfx = "boom" if ("won" in p_lower or "collapsed" in p_lower or idx == 0) else "pop"

        scenes.append({
            "beat": f"beat_{idx+1}",
            "text": p,
            "environment": env,
            "elements": elements,
            "characters": chars,
            "props": props,
            "camera": cam,
            "sfx": sfx
        })

    return {
        "id": "converted_story",
        "title": title,
        "scenes": scenes
    }
