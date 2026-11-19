"""
HyperClip AI - Content Reach Shield & Text Sanitizer
Protects YouTube Shorts and Instagram Reels reach by eliminating, masking,
and substituting shadowban-triggering words (swears, slurs, illicit drugs, violence, adult terms).
Ensures maximum algorithmic distribution to non-followers and FYP/feed discovery.
"""

import re
from typing import Tuple, List

# Dictionary of high-risk terms and algorithm-friendly replacements
# Keys are regex word-boundary patterns; values are safe replacements
CENSOR_REPLACEMENTS = [
    # Illicit Drugs & Controlled Substances (Severe IG/YT distribution killer)
    (r"\bcocaine\b", "contraband"),
    (r"\bheroin\b", "contraband"),
    (r"\bmeth\b", "contraband"),
    (r"\bfentanyl\b", "contraband"),
    (r"\bpercocet\b", "painkillers"),
    (r"\bpercs?\b", "pills"),
    (r"\boverdose\b", "emergency"),
    (r"\bcrackhead\b", "wild npc"),
    
    # Severe Slurs & Hate Speech (Immediate account strike/shadowban)
    (r"\bnigg[a-z]*\b", "n****"),
    (r"\bfag(?:got)?s?\b", "f***"),
    (r"\bretard(?:ed)?\b", "foolish"),
    (r"\btranny\b", "t*****"),
    (r"\bchink\b", "c****"),
    (r"\bspic\b", "s***"),
    (r"\bkike\b", "k***"),
    
    # Hard Swears & Vulgarities (Restricts recommendation to mature audience only)
    (r"\bmotherfuck(?:er|ing|a)?\b", "m*****"),
    (r"\bfuck(?:ing|ed|er)?s?\b", "f***"),
    (r"\bfck(?:ing)?\b", "f***"),
    (r"\bfuk(?:ing)?\b", "f***"),
    (r"\bshit(?:ting|ty)?s?\b", "sh*t"),
    (r"\bbullshit\b", "nonsense"),
    (r"\bdipshit\b", "fool"),
    (r"\bbitch(?:es|ing)?\b", "b***h"),
    (r"\bbtch\b", "b***h"),
    (r"\basshole\b", "a**hole"),
    (r"\bdumbass\b", "dumb***"),
    (r"\bjackass\b", "jack***"),
    (r"\bcunt\b", "c**t"),
    (r"\bdick(?:head)?s?\b", "d**k"),
    (r"\bpussy\b", "p***y"),
    (r"\bcock\b", "c*ck"),
    (r"\bbastard\b", "b*****d"),
    (r"\bwhore\b", "w***e"),
    (r"\bslut\b", "sl*t"),
    
    # Adult / NSFW / Sexually Explicit
    (r"\bporn(?:ography)?\b", "p*rn"),
    (r"\bnsfw\b", "censored"),
    (r"\bblowjob\b", "b*****b"),
    (r"\bdildo\b", "toy"),
    (r"\btits\b", "chest"),
    (r"\bboobs\b", "chest"),
    
    # Violence & Self-Harm (Trigger words for sensitivity flags)
    (r"\bsuicid[a-z]*\b", "self-harm"),
    (r"\bmurder(?:ed|er|ing)?s?\b", "eliminated"),
    (r"\brape(?:d|s|ing)?\b", "assault"),
]

COMPILED_RULES = [
    (re.compile(pattern, re.IGNORECASE), replacement)
    for pattern, replacement in CENSOR_REPLACEMENTS
]


def sanitize_text_for_reach(text: str) -> str:
    """
    Sanitizes titles, captions, and hooks so they adhere strictly to
    YouTube and Instagram recommendation guidelines, preventing algorithmic suppression.
    Preserves casing style (UPPERCASE or Capitalized) of the original match where applicable.
    """
    if not text:
        return text

    sanitized = text

    for regex, replacement in COMPILED_RULES:
        def _match_replacer(m: re.Match) -> str:
            matched_str = m.group(0)
            if matched_str.isupper():
                return replacement.upper()
            elif matched_str.istitle():
                return replacement.capitalize()
            return replacement

        sanitized = regex.sub(_match_replacer, sanitized)

    return sanitized


def find_prohibited_terms(text: str) -> List[str]:
    """Returns a list of any prohibited/sensitive words found in the text."""
    if not text:
        return []
    found = []
    for regex, _ in COMPILED_RULES:
        matches = regex.findall(text)
        if matches:
            found.extend(matches)
    return found


def is_safe_for_reach(text: str) -> Tuple[bool, List[str]]:
    """Checks whether the text is 100% clean of reach-suppressing terms."""
    terms = find_prohibited_terms(text)
    return (len(terms) == 0, terms)
