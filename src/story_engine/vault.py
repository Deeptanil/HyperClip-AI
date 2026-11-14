"""
Curated Vault of High-Engagement Stories.
Covers:
1. Bizarre Historical Incidents
2. Mythology & Folklore
3. Clever / Humorous True Tales
All scripts follow a 5-to-7 beat visual narrative structure (60-120s duration).
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
                "characters": [{"id": "narrator", "style": "bw", "emotion": "shocked", "pose": "hands_up"}],
                "props": ["flag"],
                "camera": "normal",
                "sfx": "boom"
            },
            {
                "beat": "absurd_setup",
                "text": "The organizers wanted to test human limits, so they provided only one water station across twenty-six miles of dirt roads in ninety-degree heat.",
                "environment": "desert",
                "characters": [{"id": "organizer", "style": "colored", "color": "#E11D48", "emotion": "smug", "pose": "shrug"}],
                "props": ["water_bottle"],
                "camera": "normal",
                "sfx": "pop"
            },
            {
                "beat": "escalation_1",
                "text": "Cars drove in front of the runners, kicking up massive clouds of dust that coated their lungs like cement. One runner collapsed vomiting blood and nearly suffocated on the side of the road.",
                "environment": "dust_road",
                "characters": [{"id": "runner_1", "style": "bw", "emotion": "deadpan", "pose": "facepalm"}],
                "props": ["dust_cloud"],
                "camera": "zoom_in",
                "sfx": "whoosh"
            },
            {
                "beat": "escalation_2",
                "text": "A Cuban postman showed up in street clothes, chopped off his trousers into shorts, got hungry mid-race, ate rotten apples from an orchard, and took a nap in an open ditch.",
                "environment": "orchard",
                "characters": [{"id": "postman", "style": "colored", "color": "#0284C7", "emotion": "scheming", "pose": "pointing"}],
                "props": ["apple"],
                "camera": "normal",
                "sfx": "pop"
            },
            {
                "beat": "climax",
                "text": "Meanwhile, the man who actually won had to be carried across the line by his trainers while hallucinating after they injected him with rat poison and brandy to keep his heart beating.",
                "environment": "finish_line",
                "characters": [{"id": "winner", "style": "colored", "color": "#16A34A", "emotion": "shocked", "pose": "hands_up"}],
                "props": ["syringe", "trophy"],
                "camera": "shake",
                "sfx": "boom"
            },
            {
                "beat": "resolution",
                "text": "He lost eight pounds, was stripped of the medal for medical fraud, and swore on his mother's grave he would never run another marathon as long as he lived.",
                "environment": "podium",
                "characters": [{"id": "winner", "style": "colored", "color": "#16A34A", "emotion": "deadpan", "pose": "facepalm"}],
                "props": ["medal"],
                "camera": "zoom_in",
                "sfx": "whoosh"
            }
        ]
    },
    {
        "id": "thors_wedding_dress",
        "category": "mythology",
        "title": "When Thor Had to Put on a Wedding Dress",
        "hook": "When Thor woke up and found his sacred hammer stolen, the price to get it back was horrifying: he had to marry the King of the Giants.",
        "scenes": [
            {
                "beat": "cold_hook",
                "text": "One morning, Thor woke up in Asgard and reached for his mighty hammer, Mjolnir. It was gone. The Giant King Thrym had buried it eight miles under the earth.",
                "environment": "palace",
                "characters": [{"id": "thor", "style": "colored", "color": "#DC2626", "emotion": "raging", "pose": "hands_up"}],
                "props": ["hammer"],
                "camera": "zoom_in",
                "sfx": "boom"
            },
            {
                "beat": "absurd_setup",
                "text": "Thrym had one ransom demand: give him the goddess Freyja as his bride, or the hammer stays buried forever. Freyja politely told the gods to jump off a cliff.",
                "environment": "council",
                "characters": [{"id": "freyja", "style": "colored", "color": "#EC4899", "emotion": "disgusted", "pose": "shrug"}],
                "props": ["scroll"],
                "camera": "normal",
                "sfx": "pop"
            },
            {
                "beat": "escalation_1",
                "text": "So Heimdall pitched a ridiculous solution: dress the beefiest, beardiest god in the cosmos in bridal silk, veil his hairy face, and pretend he's the bride.",
                "environment": "dressing_room",
                "characters": [
                    {"id": "heimdall", "style": "colored", "color": "#F59E0B", "emotion": "scheming", "pose": "pointing"},
                    {"id": "thor", "style": "colored", "color": "#DC2626", "emotion": "deadpan", "pose": "facepalm"}
                ],
                "props": ["dress"],
                "camera": "normal",
                "sfx": "whoosh"
            },
            {
                "beat": "escalation_2",
                "text": "At the wedding banquet, Thor blew his cover immediately by devouring an entire ox, eight salmon, and three barrels of mead in one sitting.",
                "environment": "banquet",
                "characters": [{"id": "thor", "style": "colored", "color": "#DC2626", "emotion": "chewing", "pose": "hands_up"}],
                "props": ["meat", "mug"],
                "camera": "zoom_in",
                "sfx": "pop"
            },
            {
                "beat": "climax",
                "text": "When Thrym lifted the veil for a kiss, he jumped back in terror because Thor's eyes were glowing with molten lightning. Loki quickly lied: 'Oh, she hasn't slept in a week from excitement.'",
                "environment": "banquet",
                "characters": [{"id": "thrym", "style": "colored", "color": "#475569", "emotion": "shocked", "pose": "hands_up"}],
                "props": ["veil"],
                "camera": "shake",
                "sfx": "boom"
            },
            {
                "beat": "resolution",
                "text": "The moment Thrym laid Mjolnir on the bride's lap for the sacred blessing, Thor dropped the bouquet, shattered the entire room, and walked out the door in high heels.",
                "environment": "ruins",
                "characters": [{"id": "thor", "style": "colored", "color": "#DC2626", "emotion": "smug", "pose": "pointing"}],
                "props": ["hammer"],
                "camera": "zoom_in",
                "sfx": "whoosh"
            }
        ]
    },
    {
        "id": "eiffel_tower_scam",
        "category": "humor",
        "title": "The Con Man Who Sold the Eiffel Tower Twice",
        "hook": "In 1925, an Austrian gentleman sold 7,000 tons of the Eiffel Tower to a Parisian scrap metal dealer for a suitcase full of francs. Then he did it again.",
        "scenes": [
            {
                "beat": "cold_hook",
                "text": "In 1925, the Eiffel Tower was in terrible shape. Paris was debating whether to tear it down, and one man read the morning newspaper and saw the heist of the century.",
                "environment": "paris_street",
                "characters": [{"id": "lustig", "style": "colored", "color": "#0D9488", "emotion": "scheming", "pose": "pointing"}],
                "props": ["newspaper"],
                "camera": "normal",
                "sfx": "pop"
            },
            {
                "beat": "absurd_setup",
                "text": "Victor Lustig faked official government stationery, booked a luxury suite at the Hotel de Crillon, and invited the city's top five scrap metal dealers for a top-secret meeting.",
                "environment": "hotel_suite",
                "characters": [{"id": "lustig", "style": "colored", "color": "#0D9488", "emotion": "smug", "pose": "shrug"}],
                "props": ["briefcase"],
                "camera": "normal",
                "sfx": "whoosh"
            },
            {
                "beat": "escalation_1",
                "text": "He told them the maintenance costs were bankrupting Paris, and the government was discreetly auctioning off seven thousand tons of wrought iron to the highest bidder.",
                "environment": "hotel_suite",
                "characters": [{"id": "dealer", "style": "bw", "emotion": "curious", "pose": "thinking"}],
                "props": ["contract"],
                "camera": "zoom_in",
                "sfx": "pop"
            },
            {
                "beat": "escalation_2",
                "text": "One dealer named André Poisson was desperate to make a name for himself. Lustig even pretended to take a bribe on top of the bid just to convince him the deal was real corrupt government business.",
                "environment": "dark_room",
                "characters": [
                    {"id": "dealer", "style": "bw", "emotion": "sweating", "pose": "hands_up"},
                    {"id": "lustig", "style": "colored", "color": "#0D9488", "emotion": "scheming", "pose": "pointing"}
                ],
                "props": ["cash_bag"],
                "camera": "normal",
                "sfx": "pop"
            },
            {
                "beat": "climax",
                "text": "Poisson handed over fifty thousand dollars in cash. Lustig packed his bags, caught the midnight train to Vienna, and waited for the police sirens that never came.",
                "environment": "train_station",
                "characters": [{"id": "lustig", "style": "colored", "color": "#0D9488", "emotion": "laughing", "pose": "hands_up"}],
                "props": ["briefcase"],
                "camera": "shake",
                "sfx": "boom"
            },
            {
                "beat": "resolution",
                "text": "Poisson was so embarrassed at being conned into buying a national landmark that he never reported it to the police. So six months later, Lustig came back to Paris and sold it a second time.",
                "environment": "eiffel_tower",
                "characters": [{"id": "lustig", "style": "colored", "color": "#0D9488", "emotion": "smug", "pose": "pointing"}],
                "props": ["hat"],
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
