"""
Curated Vault of High-Engagement Stories.
Includes explicit scene elements: vehicles, buildings, trees, and rich multi-character poses.
"""

STORY_VAULT = [
    {
        "id": "olympic_marathon_1904",
        "category": "history",
        "title": "The Worst Olympic Event in Human History",
        "hook": "In 1904, thirty-two men lined up for the Olympic marathon in St. Louis. Only fourteen survived the finish line.",
        "scenes": [
            {
                "beat": "cold_hook",
                "text": "In 1904, thirty-two athletes lined up for the Olympic marathon in St. Louis. Only fourteen made it across the finish line, and one of them literally hitched a ride in a car.",
                "environment": "stadium",
                "elements": [
                    {"type": "nature", "name": "clouds", "x": 250, "y": 250, "scale": 0.8},
                    {"type": "nature", "name": "clouds", "x": 800, "y": 320, "scale": 0.9}
                ],
                "characters": [
                    {"id": "runner_1", "style": "colored", "color": "#2563EB", "emotion": "talking", "pose": "running", "x": 420},
                    {"id": "runner_2", "style": "bw", "emotion": "shocked", "pose": "running", "x": 700}
                ],
                "props": ["flag"],
                "camera": "normal",
                "sfx": "boom"
            },
            {
                "beat": "absurd_setup",
                "text": "The organizers wanted to test human limits, so they provided only one water station across twenty-six miles of dirt roads in ninety-degree heat.",
                "environment": "dust_road",
                "elements": [
                    {"type": "nature", "name": "mountain", "x": 820, "y": 1320, "scale": 0.8},
                    {"type": "nature", "name": "clouds", "x": 350, "y": 280, "scale": 0.7}
                ],
                "characters": [
                    {"id": "organizer", "style": "colored", "color": "#DC2626", "emotion": "smug", "pose": "shrug", "x": 540}
                ],
                "props": ["bottle"],
                "camera": "normal",
                "sfx": "pop"
            },
            {
                "beat": "escalation_1",
                "text": "Cars drove in front of the runners, kicking up massive clouds of dust that coated their lungs like cement. One runner collapsed vomiting blood and nearly suffocated on the side of the road.",
                "environment": "dust_road",
                "elements": [
                    {"type": "vehicle", "name": "vintage_car", "x": 820, "y": 1420, "scale": 1.05, "color": "#991B1B"}
                ],
                "characters": [
                    {"id": "collapsed_runner", "style": "bw", "emotion": "deadpan", "pose": "collapsed", "x": 340}
                ],
                "props": [],
                "camera": "zoom_in",
                "sfx": "whoosh"
            },
            {
                "beat": "escalation_2",
                "text": "A Cuban postman showed up in street clothes, chopped off his trousers into shorts, got hungry mid-race, ate rotten apples from an orchard, and took a nap in an open ditch.",
                "environment": "orchard",
                "elements": [
                    {"type": "nature", "name": "apple_tree", "x": 220, "y": 1450, "scale": 1.0},
                    {"type": "nature", "name": "apple_tree", "x": 860, "y": 1450, "scale": 0.95}
                ],
                "characters": [
                    {"id": "postman", "style": "colored", "color": "#0284C7", "emotion": "deadpan", "pose": "napping", "x": 540, "y": 1450}
                ],
                "props": ["apple"],
                "camera": "normal",
                "sfx": "pop"
            },
            {
                "beat": "climax",
                "text": "Meanwhile, the man who actually won had to be carried across the line by his trainers while hallucinating after they injected him with rat poison and brandy to keep his heart beating.",
                "environment": "finish_line",
                "elements": [
                    {"type": "architecture", "name": "finish_banner", "x": 540, "y": 1360, "scale": 1.0}
                ],
                "characters": [
                    {"id": "winner", "style": "colored", "color": "#16A34A", "emotion": "shocked", "pose": "hands_up", "x": 420},
                    {"id": "trainer", "style": "bw", "emotion": "scheming", "pose": "pointing", "x": 680}
                ],
                "props": ["trophy"],
                "camera": "shake",
                "sfx": "boom"
            },
            {
                "beat": "resolution",
                "text": "He lost eight pounds, was stripped of the medal for medical fraud, and swore on his mother's grave he would never run another marathon as long as he lived.",
                "environment": "stadium",
                "elements": [
                    {"type": "nature", "name": "clouds", "x": 540, "y": 250, "scale": 0.9}
                ],
                "characters": [
                    {"id": "winner", "style": "colored", "color": "#16A34A", "emotion": "deadpan", "pose": "facepalm", "x": 540}
                ],
                "props": ["medal"],
                "camera": "zoom_in",
                "sfx": "whoosh"
            }
        ]
    },
    {
        "id": "eiffel_tower_scam",
        "category": "humor",
        "title": "The Con Man Who Sold the Eiffel Tower Twice",
        "hook": "In 1925, an Austrian gentleman sold 7,000 tons of the Eiffel Tower to a scrap metal dealer for a suitcase full of cash. Then he did it again.",
        "scenes": [
            {
                "beat": "cold_hook",
                "text": "In 1925, the Eiffel Tower was in terrible shape. Paris was debating whether to tear it down, and one man read the morning newspaper and saw the heist of the century.",
                "environment": "paris_street",
                "elements": [
                    {"type": "architecture", "name": "city_building", "x": 200, "y": 1420, "scale": 0.85},
                    {"type": "architecture", "name": "city_building", "x": 880, "y": 1420, "scale": 0.85}
                ],
                "characters": [
                    {"id": "lustig", "style": "colored", "color": "#0D9488", "emotion": "scheming", "pose": "pointing", "x": 540}
                ],
                "props": ["newspaper"],
                "camera": "normal",
                "sfx": "pop"
            },
            {
                "beat": "absurd_setup",
                "text": "Victor Lustig faked official government stationery, booked a luxury suite at the Hotel de Crillon, and invited the city's top scrap metal dealers for a secret meeting.",
                "environment": "hotel_suite",
                "elements": [],
                "characters": [
                    {"id": "lustig", "style": "colored", "color": "#0D9488", "emotion": "smug", "pose": "shrug", "x": 380},
                    {"id": "dealer", "style": "bw", "emotion": "deadpan", "pose": "stand", "x": 700}
                ],
                "props": ["briefcase"],
                "camera": "normal",
                "sfx": "whoosh"
            },
            {
                "beat": "escalation_1",
                "text": "He told them the maintenance costs were bankrupting Paris, and the government was discreetly auctioning off seven thousand tons of wrought iron to the highest bidder.",
                "environment": "hotel_suite",
                "elements": [],
                "characters": [
                    {"id": "dealer", "style": "bw", "emotion": "shocked", "pose": "hands_up", "x": 540}
                ],
                "props": ["briefcase"],
                "camera": "zoom_in",
                "sfx": "pop"
            },
            {
                "beat": "escalation_2",
                "text": "One dealer named André Poisson was desperate to make a name for himself. Lustig even pretended to take a bribe on top of the bid just to convince him the deal was real corrupt government business.",
                "environment": "paris_street",
                "elements": [
                    {"type": "architecture", "name": "city_building", "x": 180, "y": 1420, "scale": 0.85}
                ],
                "characters": [
                    {"id": "dealer", "style": "bw", "emotion": "sweating", "pose": "facepalm", "x": 360},
                    {"id": "lustig", "style": "colored", "color": "#0D9488", "emotion": "scheming", "pose": "pointing", "x": 720}
                ],
                "props": ["cash_bag"],
                "camera": "normal",
                "sfx": "pop"
            },
            {
                "beat": "climax",
                "text": "Poisson handed over fifty thousand dollars in cash. Lustig packed his bags, caught the midnight train to Vienna, and waited for the police sirens that never came.",
                "environment": "dust_road",
                "elements": [
                    {"type": "vehicle", "name": "train", "x": 540, "y": 1400, "scale": 1.0}
                ],
                "characters": [
                    {"id": "lustig", "style": "colored", "color": "#0D9488", "emotion": "laughing", "pose": "celebrating", "x": 540}
                ],
                "props": ["cash_bag"],
                "camera": "shake",
                "sfx": "boom"
            },
            {
                "beat": "resolution",
                "text": "Poisson was so embarrassed at being conned into buying a national landmark that he never reported it to the police. So six months later, Lustig came back to Paris and sold it a second time.",
                "environment": "eiffel_tower",
                "elements": [
                    {"type": "architecture", "name": "city_building", "x": 160, "y": 1450, "scale": 0.8},
                    {"type": "architecture", "name": "city_building", "x": 920, "y": 1450, "scale": 0.8}
                ],
                "characters": [
                    {"id": "lustig", "style": "colored", "color": "#0D9488", "emotion": "smug", "pose": "celebrating", "x": 540}
                ],
                "props": ["trophy"],
                "camera": "zoom_in",
                "sfx": "whoosh"
            }
        ]
    }
]

def get_vault_story(category=None, story_id=None):
    import random
    if story_id:
        for s in STORY_VAULT:
            if s["id"] == story_id:
                return s
    filtered = STORY_VAULT
    if category:
        filtered = [s for s in STORY_VAULT if s["category"] == category]
        if not filtered:
            filtered = STORY_VAULT
    return random.choice(filtered)
