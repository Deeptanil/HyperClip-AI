"""
Verify all YouTube Short upload URLs in posted_twitch_log.json via YouTube oEmbed API.
Checks if each video is live, public, and active.
"""

import json
import urllib.request
import sys

def check_video(vid_url):
    vid = vid_url.rstrip("/").split("/")[-1]
    oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={vid}&format=json"
    try:
        req = urllib.request.Request(oembed_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            res = json.loads(r.read().decode("utf-8"))
            return True, res.get("title", ""), res.get("author_name", "")
    except Exception as e:
        return False, str(e), ""

def main():
    try:
        with open("posted_twitch_log.json", "r", encoding="utf-8") as f:
            logs = json.load(f)
    except Exception as e:
        print(f"Failed to read posted_twitch_log.json: {e}")
        return

    print(f"Total log entries: {len(logs)}\n")
    yt_entries = []
    for entry in logs:
        uploads = entry.get("uploads", {})
        ts = entry.get("timestamp", "")
        for k, v in uploads.items():
            if "youtube" in k and isinstance(v, str) and "shorts" in v:
                yt_entries.append((ts, v, entry.get("clips_used", [])))

    print(f"Found {len(yt_entries)} YouTube upload records:\n")
    live_count = 0
    for ts, url, clips in yt_entries:
        is_live, title, author = check_video(url)
        cname = clips[0] if clips else "unknown"
        if is_live:
            live_count += 1
            print(f"[LIVE] {ts[:19]} | {url} | '{title}' by @{author} (Clip: {cname})")
        else:
            print(f"[NOT LIVE / PENDING] {ts[:19]} | {url} | Reason: {title} (Clip: {cname})")

    print(f"\nSummary: {live_count}/{len(yt_entries)} YouTube Shorts verified LIVE and publicly visible.")

if __name__ == "__main__":
    main()
