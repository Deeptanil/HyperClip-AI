"""
Twitch Public GQL Client (Zero-Cost, No OAuth Secret Required).
Queries streamer live status, active stream uptime, game category,
live archive VOD ID, and recent past VODs.
"""

import requests
from datetime import datetime, timezone

TWITCH_GQL_URL = "https://gql.twitch.tv/gql"
TWITCH_CLIENT_ID = "kimne78kx3ncx6brgo4mv6wki5h1ko"


def _gql_request(query: str, variables: dict = None) -> dict:
    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Content-Type": "application/json",
    }
    payload = {"query": query, "variables": variables or {}}
    resp = requests.post(TWITCH_GQL_URL, json=payload, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()


def get_streamer_status(username: str) -> dict:
    """
    Fetches live stream info + recent archive VODs for a Twitch login.
    Returns normalized dict with is_live, live_minutes, game, live_vod_id, and recent_vods.
    """
    query = """
    query($login: String!) {
      user(login: $login) {
        id
        login
        displayName
        stream {
          id
          title
          createdAt
          viewersCount
          game {
            name
          }
          archiveVideo {
            id
          }
        }
        videos(first: 3, type: ARCHIVE) {
          edges {
            node {
              id
              title
              createdAt
              lengthSeconds
              viewCount
              game {
                name
              }
            }
          }
        }
      }
    }
    """
    data = _gql_request(query, {"login": username.lower()})
    user = data.get("data", {}).get("user")
    if not user:
        return {"username": username, "exists": False, "is_live": False, "recent_vods": []}

    now = datetime.now(timezone.utc)
    stream = user.get("stream")
    is_live = stream is not None

    live_info = None
    if is_live:
        created_at = datetime.fromisoformat(stream["createdAt"].replace("Z", "+00:00"))
        live_minutes = (now - created_at).total_seconds() / 60.0
        game_name = (stream.get("game") or {}).get("name", "Unknown")
        archive_vod = (stream.get("archiveVideo") or {}).get("id")
        live_info = {
            "stream_id": stream.get("id"),
            "title": stream.get("title", ""),
            "game": game_name,
            "viewers": stream.get("viewersCount", 0),
            "live_minutes": round(live_minutes, 1),
            "vod_id": archive_vod,
            "created_at": stream["createdAt"],
        }

    recent_vods = []
    for edge in (user.get("videos") or {}).get("edges", []):
        node = edge.get("node") or {}
        if not node.get("id"):
            continue
        created_at = datetime.fromisoformat(node["createdAt"].replace("Z", "+00:00"))
        age_hours = (now - created_at).total_seconds() / 3600.0
        recent_vods.append({
            "vod_id": node["id"],
            "title": node.get("title", ""),
            "game": (node.get("game") or {}).get("name", "Unknown"),
            "length_seconds": node.get("lengthSeconds", 0),
            "age_hours": round(age_hours, 2),
            "created_at": node["createdAt"],
        })

    return {
        "username": user["login"],
        "display_name": user["displayName"],
        "exists": True,
        "is_live": is_live,
        "live": live_info,
        "recent_vods": recent_vods,
    }


def find_clippable_targets(config: dict) -> list:
    """
    Scans configured streamers and returns a list of eligible VOD targets.
    Prioritizes:
      1. Live streams that have been running >= min_stream_minutes (playing target game if specified).
      2. Recent archived VODs (< past_vod_max_age_hours) if check_past_vods_if_offline is true.
    """
    tc = config.get("twitch_clipper", {})
    streamers = tc.get("streamers", [])
    target_games = [g.lower() for g in tc.get("target_games", []) if g]
    min_minutes = tc.get("min_stream_minutes", 30)
    check_past = tc.get("check_past_vods_if_offline", True)
    max_age_h = tc.get("past_vod_max_age_hours", 24)

    targets = []
    for login in streamers:
        try:
            status = get_streamer_status(login)
        except Exception as e:
            print(f"[!] GQL error for {login}: {e}")
            continue

        if not status.get("exists"):
            print(f"[-] Streamer '{login}' not found on Twitch.")
            continue

        display = status["display_name"]

        # 1. Check live stream
        if status["is_live"] and status["live"]:
            live = status["live"]
            game_match = (not target_games) or (live["game"].lower() in target_games)
            if live["live_minutes"] >= min_minutes and game_match and live["vod_id"]:
                targets.append({
                    "username": status["username"],
                    "display_name": display,
                    "vod_id": live["vod_id"],
                    "title": live["title"],
                    "game": live["game"],
                    "is_live": True,
                    "duration_sec": int(live["live_minutes"] * 60),
                    "viewers": live["viewers"],
                })
                continue

        # 2. Check recent archived VODs if offline or live stream didn't match yet
        if check_past:
            for vod in status["recent_vods"]:
                game_match = (not target_games) or (vod["game"].lower() in target_games)
                if vod["age_hours"] <= max_age_h and vod["length_seconds"] >= 600 and game_match:
                    targets.append({
                        "username": status["username"],
                        "display_name": display,
                        "vod_id": vod["vod_id"],
                        "title": vod["title"],
                        "game": vod["game"],
                        "is_live": False,
                        "duration_sec": vod["length_seconds"],
                        "age_hours": vod["age_hours"],
                    })
                    break

    return targets
