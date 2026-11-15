"""
Twitch Chat Velocity & Hype Spike Detector.
Analyzes TwitchDownloaderCLI chat.json logs using sliding-window density
and emote/keyword weighting to pinpoint viral highlight timestamps.
"""

import json
import math
import re
from collections import defaultdict

BOT_USERS = {"nightbot", "streamelements", "streamlabs", "moobot", "fossabot", "wizebot"}

HYPE_PATTERNS = re.compile(
    r"\b(omegalul|kekw|lulw|lul|lmao|lmfao|pog|poggers|pogchamp|clip|clipped|"
    r"no way|wtf|what|insane|crazy|bro|gyat|sheesh|cooked|cinema|peak|"
    r"w+|l+)\b|[💀😭🔥🤯😂]",
    re.IGNORECASE,
)


def detect_hype_moments(
    chat_json_path: str,
    pre_peak_sec: int = 22,
    post_peak_sec: int = 13,
    max_clips: int = 4,
    min_spacing_sec: int = 180,
    min_spike_sigma: float = 2.0,
    min_messages_per_window: int = 12,
    bucket_sec: int = 5,
    viewers: int = 0,
    intro_skip_sec: int = 480,
) -> list:
    """
    Parses chat JSON and returns top distinct highlight moments sorted by score.
    - Cuts out stream starting screens via `intro_skip_sec` (auto-scaled for shorter VODs).
    - Scales chat velocity threshold dynamically based on live `viewers` count
      (or stream baseline velocity if `viewers == 0`) so mega-chats and mid-size
      creators are both judged fairly.
    """
    with open(chat_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    comments = data.get("comments", [])
    if not comments:
        return []

    buckets = defaultdict(lambda: {"count": 0, "score": 0.0, "texts": []})
    max_offset = 0.0

    for c in comments:
        commenter = ((c.get("commenter") or {}).get("name") or "").lower()
        if commenter in BOT_USERS:
            continue

        offset = float(c.get("content_offset_seconds", 0.0))
        if offset < 0:
            continue
        if offset > max_offset:
            max_offset = offset

        body = ((c.get("message") or {}).get("body") or "").strip()
        if not body:
            continue

        b_idx = int(offset // bucket_sec)
        hype_hits = len(HYPE_PATTERNS.findall(body))
        weight = 1.0 + min(hype_hits, 3) * 0.75

        buckets[b_idx]["count"] += 1
        buckets[b_idx]["score"] += weight
        if len(buckets[b_idx]["texts"]) < 6:
            buckets[b_idx]["texts"].append(body)

    if max_offset < 30 or not buckets:
        return []

    # Cut out "Stream Starting Soon" / intro screens:
    # Full streams (>= 20m) skip `intro_skip_sec` (default 8 min); shorter VODs skip 15% (min 90s).
    effective_intro_skip = intro_skip_sec if max_offset >= 1200 else min(intro_skip_sec, max(90, int(max_offset * 0.15)))
    intro_bucket_cutoff = int(effective_intro_skip // bucket_sec)

    num_buckets = int(max_offset // bucket_sec) + 1
    # 3-bucket (15-second) rolling window
    rolling_scores = []
    rolling_counts = []
    for i in range(num_buckets):
        s = sum(buckets[j]["score"] for j in range(max(0, i - 1), min(num_buckets, i + 2)))
        cnt = sum(buckets[j]["count"] for j in range(max(0, i - 1), min(num_buckets, i + 2)))
        rolling_scores.append(s)
        rolling_counts.append(cnt)

    # Compute baseline strictly from post-intro active windows
    post_intro_scores = [rolling_scores[i] for i in range(intro_bucket_cutoff, num_buckets) if rolling_scores[i] > 0]
    post_intro_counts = [rolling_counts[i] for i in range(intro_bucket_cutoff, num_buckets) if rolling_counts[i] > 0]
    if len(post_intro_scores) < 5:
        return []

    mean_score = sum(post_intro_scores) / len(post_intro_scores)
    mean_count = sum(post_intro_counts) / len(post_intro_counts)
    variance = sum((s - mean_score) ** 2 for s in post_intro_scores) / len(post_intro_scores)
    std_score = math.sqrt(variance)

    # Scale minimum messages per 15s window by viewer count (or baseline chat speed)
    if viewers > 0:
        if viewers < 3000:
            viewer_floor = max(6, int(viewers * 0.0025))
        elif viewers < 20000:
            viewer_floor = max(10, int(viewers * 0.0018))
        else:
            viewer_floor = max(25, min(140, int(viewers * 0.0012)))
        effective_min_msgs = max(viewer_floor, int(mean_count * 1.65))
    else:
        effective_min_msgs = max(min_messages_per_window, int(mean_count * 1.75))

    threshold = mean_score + (min_spike_sigma * std_score)

    # Collect candidate peaks (local maxima above threshold and viewer-scaled message count)
    candidates = []
    for i in range(max(1, intro_bucket_cutoff), num_buckets - 1):
        s = rolling_scores[i]
        cnt = rolling_counts[i]
        if s >= threshold and cnt >= effective_min_msgs:
            if s >= rolling_scores[i - 1] and s >= rolling_scores[i + 1]:
                peak_sec = i * bucket_sec + (bucket_sec // 2)
                if peak_sec < effective_intro_skip:
                    continue
                z_score = (s - mean_score) / std_score if std_score > 0 else 0.0
                sample_msgs = buckets[i]["texts"] or buckets[max(0, i - 1)]["texts"]
                candidates.append({
                    "peak_sec": int(peak_sec),
                    "start_sec": max(0, int(peak_sec - pre_peak_sec)),
                    "end_sec": int(peak_sec + post_peak_sec),
                    "score": round(s, 2),
                    "z_score": round(z_score, 2),
                    "msg_count_15s": int(cnt),
                    "min_msgs_required": int(effective_min_msgs),
                    "sample_chat": sample_msgs[:4],
                })

    # Sort highest score first and apply non-maximum suppression
    candidates.sort(key=lambda x: x["score"], reverse=True)
    selected = []
    for cand in candidates:
        too_close = any(abs(cand["peak_sec"] - sel["peak_sec"]) < min_spacing_sec for sel in selected)
        if not too_close:
            selected.append(cand)
        if len(selected) >= max_clips:
            break

    return selected
