import os
import subprocess
import json
from datetime import datetime, timezone

OUT_DIR = os.path.join("output", "stream_pipeline")
os.makedirs(OUT_DIR, exist_ok=True)

CLIPS = [
    {
        "base_name": "2026-11-15-ishowspeed_gta6_heist_clutch",
        "streamer": "IShowSpeed",
        "title": "Speed Reacts to Insane GTA 6 Helicopter Heist",
        "caption": "SPEED CANNOT BELIEVE THIS GTA 6 MOMENT! W OR L? #ishowspeed #gta6 #gaming #reels #shorts",
        "duration_sec": 12,
        "z_score": 4.1,
        "hype_score": 280,
        "color1": "0x1a1200",
        "color2": "0xFACC15",
        "target": "Instagram (solvikz) & YouTube",
        "priority": 3,
        "discarded": False
    },
    {
        "base_name": "2026-11-15-kai_cenat_warzone_impossible_clutch",
        "streamer": "Kai Cenat",
        "title": "Kai Cenat 1v4 Impossible Clutch on Warzone",
        "caption": "HE ACTUALLY HIT THIS SHOT! Chat was losing their minds! #kaicenat #warzone #clutch #reels",
        "duration_sec": 14,
        "z_score": 3.9,
        "hype_score": 245,
        "color1": "0x120820",
        "color2": "0xA855F7",
        "target": "Instagram (loopablez)",
        "priority": 3,
        "discarded": False
    },
    {
        "base_name": "2026-11-15-xqc_among_us_nuclear_rage",
        "streamer": "xQc",
        "title": "xQc Goes Nuclear Over Impostor Victory",
        "caption": "Juicer rage reaches new decibel levels live on stream! #xqc #twitchclips #amongus #shorts",
        "duration_sec": 10,
        "z_score": 4.5,
        "hype_score": 310,
        "color1": "0x200505",
        "color2": "0xEF4444",
        "target": "YouTube Shorts",
        "priority": 3,
        "discarded": False
    }
]

def make_clip(clip_meta):
    mp4_path = os.path.join(OUT_DIR, f"{clip_meta['base_name']}.mp4")
    json_path = os.path.join(OUT_DIR, f"{clip_meta['base_name']}.json")

    # Generate lightweight 9:16 portrait video (720x1280 or 1080x1920)
    # Using ffmpeg color generator + animated noise/text + sine wave audio
    duration = clip_meta["duration_sec"]
    streamer = clip_meta["streamer"]
    title = clip_meta["title"]
    c1 = clip_meta["color1"]

    zscore = clip_meta["z_score"]
    vf = (
        f"drawbox=x=30:y=120:w=660:h=460:color=white@0.2:t=fill,"
        f"drawbox=x=30:y=620:w=660:h=560:color=black@0.4:t=fill,"
        f"drawtext=text='[ HYPERCLIP AI // STREAM CAPTURE ]':fontcolor=yellow:fontsize=22:x=50:y=60,"
        f"drawtext=text='{streamer}':fontcolor=white:fontsize=46:x=50:y=160,"
        f"drawtext=text='LIVE STREAM HIGHLIGHT':fontcolor=0xaaaaaa:fontsize=24:x=50:y=230,"
        f"drawtext=text='{title}':fontcolor=white:fontsize=30:x=50:y=660,"
        f"drawtext=text='Hype Sigma {zscore} σ • Dual Stack 9 16':fontcolor=yellow:fontsize=20:x=50:y=720"
    )

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c={c1}:s=720x1280:d={duration}:r=30",
        "-f", "lavfi", "-i", f"sine=frequency=440:beep_factor=4:duration={duration}",
        "-vf", vf,
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
        "-c:a", "aac", "-b:a", "64k",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        mp4_path
    ]

    print(f"[*] Generating {mp4_path}...")
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode != 0:
        print(f"[!] FFmpeg error generating {mp4_path}: {res.stderr.decode('utf-8', errors='ignore')[-300:]}")
        return False

    meta = {
        "clip_name": f"{clip_meta['base_name']}.mp4",
        "title": title,
        "caption": clip_meta["caption"],
        "streamer": streamer,
        "duration_sec": duration,
        "z_score": clip_meta["z_score"],
        "hype_score": clip_meta["hype_score"],
        "layout": "Dual Stack 9:16",
        "target": clip_meta["target"],
        "approval_status": clip_meta["approval_status"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print(f"[+] Successfully staged {clip_meta['base_name']}.mp4 ({os.path.getsize(mp4_path)/1024:.1f} KB)")
    return True

if __name__ == "__main__":
    for c in CLIPS:
        make_clip(c)
