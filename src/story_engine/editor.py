"""
Anti-AI Slop Editorial Critic.
Acts as a ruthless head editor to reject clichés, robotic cadence, fake suspense, and generic filler.
"""

import re
import json

# Universal AI Slop Blacklist
SLOP_PATTERNS = [
    r"\bhave you ever wondered\b",
    r"\bin a world where\b",
    r"\blittle did (he|she|they) know\b",
    r"\bthis changed everything (forever)?\b",
    r"\bdelve\b",
    r"\btapestry\b",
    r"\bbeacon\b",
    r"\btestament to\b",
    r"\bneedless to say\b",
    r"\bspoiler alert\b",
    r"\bfast forward to\b",
    r"\bin conclusion\b",
    r"\bremember guys\b",
    r"\bit turns out\b",
    r"\bunfold\b",
    r"\ba story of\b",
    r"\bharkens back\b",
    r"\blike a scene from a movie\b"
]

def analyze_slop(text):
    """Detects banned clichés and generic AI phrasing."""
    violations = []
    text_lower = text.lower()
    for pattern in SLOP_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            violations.append(match.group(0))
    return violations

def evaluate_script(script_data, client=None):
    """
    Evaluates script against the 5-point storytelling rubric.
    Returns: is_passed (bool), score (float), feedback (list of str)
    """
    scenes = script_data.get("scenes", [])
    full_text = " ".join(s.get("text", "") for s in scenes)
    
    slop_found = analyze_slop(full_text)
    feedback = []

    # Slop Penalty
    slop_score = max(0.0, 10.0 - (len(slop_found) * 2.5))
    if slop_found:
        feedback.append(f"Contains AI Slop clichés: {', '.join(set(slop_found))}")

    # Hook Strength Check (Must jump straight into action/conflict)
    first_sentence = scenes[0].get("text", "") if scenes else ""
    hook_score = 10.0
    if re.search(r"^(today|in this video|have you ever|what if|let me tell you)", first_sentence, re.IGNORECASE):
        hook_score -= 4.0
        feedback.append("Weak hook: Starts with preamble or meta-talk instead of in-medias-res conflict.")

    # Duration Check (Target 60-120 seconds: ~130 - 260 spoken words)
    word_count = len(full_text.split())
    length_score = 10.0
    if word_count < 110:
        length_score -= 3.0
        feedback.append(f"Script too short ({word_count} words). Target: 130-260 words for 60-120s.")
    elif word_count > 300:
        length_score -= 3.0
        feedback.append(f"Script too long ({word_count} words). Exceeds 120s vertical format.")

    # Narrative Escalation Check (At least 4-7 dynamic visual scenes)
    scene_score = 10.0
    if len(scenes) < 4:
        scene_score -= 3.0
        feedback.append(f"Only {len(scenes)} scenes. Minimum 5 distinct beats required for dynamic visual storytelling.")

    # Weighted Average Score
    final_score = (slop_score * 0.35) + (hook_score * 0.25) + (length_score * 0.20) + (scene_score * 0.20)
    is_passed = final_score >= 8.5 and len(slop_found) == 0

    return {
        "passed": is_passed,
        "score": round(final_score, 1),
        "word_count": word_count,
        "estimated_duration_sec": round(word_count / 2.3, 1),
        "violations": slop_found,
        "feedback": feedback
    }

if __name__ == "__main__":
    sample = {
        "title": "The 1904 Olympic Marathon",
        "scenes": [
            {"text": "Have you ever wondered what the worst race in human history looked like?"},
            {"text": "In 1904, thirty-two men lined up in St. Louis during a blistering heatwave."}
        ]
    }
    result = evaluate_script(sample)
    print("Evaluation:", json.dumps(result, indent=2))
