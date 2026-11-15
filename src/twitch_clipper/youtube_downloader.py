"""
YouTube Stream & Slice Downloader (powered by yt-dlp).
Allows HyperClip AI to scan YouTube Live/VOD streams for creators like
IShowSpeed, Techno Gamerz, and TGG, and download precise sub-minute slices.
"""

import os
import yt_dlp
from yt_dlp.utils import download_range_func


def get_recent_channel_streams(channel_handle_or_url: str, limit: int = 3) -> list:
    """
    Fetches the most recent streams/VODs for a given YouTube channel handle or URL.
    Example handle: '@IShowSpeed' or 'https://www.youtube.com/@IShowSpeed/streams'
    """
    if not channel_handle_or_url.startswith("http"):
        url = f"https://www.youtube.com/{channel_handle_or_url.lstrip('/')}/streams"
    else:
        url = channel_handle_or_url

    ydl_opts = {
        "quiet": True,
        "extract_flat": True,
        "playlistend": limit,
    }

    results = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            entries = info.get("entries", [])
            for e in entries:
                if e.get("id"):
                    results.append({
                        "id": e.get("id"),
                        "title": e.get("title", ""),
                        "url": f"https://www.youtube.com/watch?v={e.get('id')}",
                    })
    except Exception as e:
        print(f"[!] Error querying YouTube channel {channel_handle_or_url}: {e}")

    return results


def get_youtube_video_metadata(video_url_or_id: str) -> dict:
    """Extracts title, duration, and live status without downloading the media."""
    url = video_url_or_id if video_url_or_id.startswith("http") else f"https://www.youtube.com/watch?v={video_url_or_id}"
    ydl_opts = {"quiet": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            "id": info.get("id"),
            "title": info.get("title", ""),
            "duration": info.get("duration", 0),
            "live_status": info.get("live_status", ""),
            "url": url,
        }


def download_youtube_slice(video_url_or_id: str, start_s: int, end_s: int, output_path: str) -> str:
    """
    Downloads an exact time slice (sub-minute) from a YouTube video/stream using yt-dlp
    without downloading the entire stream file.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    if os.path.exists(output_path):
        try:
            os.remove(output_path)
        except OSError:
            pass

    url = video_url_or_id if video_url_or_id.startswith("http") else f"https://www.youtube.com/watch?v={video_url_or_id}"

    base_tmpl = output_path.rsplit(".", 1)[0]
    outtmpl = f"{base_tmpl}.%(ext)s"

    ydl_opts = {
        "format": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "download_ranges": download_range_func(None, [(start_s, end_s)]),
        "outtmpl": outtmpl,
        "force_keyframes_at_cuts": True,
        "quiet": False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    if os.path.exists(output_path):
        return output_path

    # Check if downloaded under alternate extension and rename/return
    for ext in ["mp4", "mkv", "webm"]:
        cand = f"{base_tmpl}.{ext}"
        if os.path.exists(cand):
            return cand

    raise RuntimeError(f"Failed to find downloaded slice at {output_path}")
