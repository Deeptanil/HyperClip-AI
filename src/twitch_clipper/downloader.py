"""
TwitchDownloaderCLI Wrapper (powered by lay295/TwitchDownloader).
Auto-installs the latest TwitchDownloaderCLI binary for Linux x64 or Windows x64
and provides clean wrappers for chatdownload and sub-minute videodownload.
"""

import os
import sys
import stat
import zipfile
import platform
import subprocess
import requests

BIN_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "tools", "bin")


def _format_hms(seconds: int) -> str:
    seconds = max(0, int(seconds))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def ensure_twitch_downloader_cli() -> str:
    """Finds or auto-downloads TwitchDownloaderCLI for the current OS."""
    is_win = platform.system().lower().startswith("win")
    exe_name = "TwitchDownloaderCLI.exe" if is_win else "TwitchDownloaderCLI"
    local_bin = os.path.join(BIN_DIR, exe_name)

    if os.path.exists(local_bin):
        return local_bin

    # Check if available in PATH
    from shutil import which
    in_path = which(exe_name)
    if in_path:
        return in_path

    os.makedirs(BIN_DIR, exist_ok=True)
    print("[*] Downloading TwitchDownloaderCLI from lay295/TwitchDownloader releases...")

    resp = requests.get("https://api.github.com/repos/lay295/TwitchDownloader/releases/latest", timeout=20)
    resp.raise_for_status()
    release = resp.json()

    target_keyword = "Windows-x64" if is_win else "Linux-x64"
    asset_url = None
    asset_name = None
    for asset in release.get("assets", []):
        name = asset.get("name", "")
        if "TwitchDownloaderCLI" in name and target_keyword in name and name.endswith(".zip"):
            asset_url = asset["browser_download_url"]
            asset_name = name
            break

    if not asset_url:
        raise RuntimeError(f"Could not find TwitchDownloaderCLI asset for {target_keyword}")

    zip_path = os.path.join(BIN_DIR, asset_name)
    with requests.get(asset_url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(zip_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(BIN_DIR)
    os.remove(zip_path)

    if not os.path.exists(local_bin):
        # Search recursively if nested in subfolder
        for root, _, files in os.walk(BIN_DIR):
            if exe_name in files:
                src = os.path.join(root, exe_name)
                os.replace(src, local_bin)
                break

    if not is_win and os.path.exists(local_bin):
        st = os.stat(local_bin)
        os.chmod(local_bin, st.st_mode | stat.S_IEXEC)

    print(f"[+] TwitchDownloaderCLI ready: {local_bin}")
    return local_bin


def download_chat(vod_id: str, output_json: str, start_sec: int = None, end_sec: int = None) -> str:
    """Downloads VOD chat JSON using TwitchDownloaderCLI chatdownload."""
    cli = ensure_twitch_downloader_cli()
    os.makedirs(os.path.dirname(os.path.abspath(output_json)), exist_ok=True)

    cmd = [
        cli, "chatdownload",
        "-u", str(vod_id),
        "-o", output_json,
        "--bttv", "false",
        "--ffz", "false",
        "--stv", "false",
        "--chat-connections", "4",
    ]
    if start_sec is not None and start_sec > 0:
        cmd.extend(["-b", _format_hms(start_sec)])
    if end_sec is not None and end_sec > 0:
        cmd.extend(["-e", _format_hms(end_sec)])

    print(f"[*] Downloading chat for VOD {vod_id}...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"chatdownload failed ({res.returncode}): {res.stderr or res.stdout}")
    return output_json


def download_video_segment(vod_id: str, start_sec: int, end_sec: int, output_mp4: str, quality: str = "1080p60") -> str:
    """Downloads only the exact highlight slice [-b, -e] from a Twitch VOD."""
    cli = ensure_twitch_downloader_cli()
    os.makedirs(os.path.dirname(os.path.abspath(output_mp4)), exist_ok=True)

    cmd = [
        cli, "videodownload",
        "-u", str(vod_id),
        "-b", _format_hms(start_sec),
        "-e", _format_hms(end_sec),
        "-q", quality,
        "-t", "4",
        "-o", output_mp4,
    ]
    print(f"[*] Downloading VOD {vod_id} segment [{_format_hms(start_sec)} -> {_format_hms(end_sec)}]...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"videodownload failed ({res.returncode}): {res.stderr or res.stdout}")
    return output_mp4
