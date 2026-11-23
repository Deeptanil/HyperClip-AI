"""
HyperClip AI - Centralized Structured Logging & Persistent Log Backup System.
Maintains persistent audit logs (human-readable .log and machine-readable .jsonl)
and automated rolling backups of all critical log and state files.
"""

import os
import json
import shutil
from datetime import datetime, timezone

LOGS_DIR = "logs"
BACKUPS_DIR = os.path.join(LOGS_DIR, "backups")
ACTIVITY_LOG = os.path.join(LOGS_DIR, "activity.log")
EVENTS_JSONL = os.path.join(LOGS_DIR, "activity_events.jsonl")

def ensure_log_dirs():
    os.makedirs(LOGS_DIR, exist_ok=True)
    os.makedirs(BACKUPS_DIR, exist_ok=True)

def log_event(level: str, component: str, action: str, details: dict | str = None):
    """
    Records a structured event in both activity.log and activity_events.jsonl.
    Levels: INFO, SUCCESS, WARNING, ERROR, CRITICAL
    """
    ensure_log_dirs()
    now_utc = datetime.now(timezone.utc)
    ts_iso = now_utc.isoformat()
    ts_display = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")

    details_str = json.dumps(details) if isinstance(details, dict) else str(details or "")
    log_line = f"[{ts_display}] [{level.upper()}] [{component}] {action}: {details_str}\n"

    try:
        with open(ACTIVITY_LOG, "a", encoding="utf-8") as f:
            f.write(log_line)
    except Exception as e:
        print(f"[!] Could not write to {ACTIVITY_LOG}: {e}")

    try:
        event_dict = {
            "timestamp": ts_iso,
            "level": level.upper(),
            "component": component,
            "action": action,
            "details": details if isinstance(details, dict) else {"message": details_str}
        }
        with open(EVENTS_JSONL, "a", encoding="utf-8") as f:
            f.write(json.dumps(event_dict) + "\n")
    except Exception as e:
        print(f"[!] Could not write to {EVENTS_JSONL}: {e}")

def backup_critical_logs():
    """
    Creates snapshots and rolling backups of posted_twitch_log.json,
    posted_log.json, and clipper_state.json into logs/backups/.
    """
    ensure_log_dirs()
    critical_files = [
        "posted_twitch_log.json",
        "posted_log.json",
        "clipper_state.json",
        "config.json",
    ]

    now_utc = datetime.now(timezone.utc)
    month_str = now_utc.strftime("%Y_%m")
    backed_up = []

    for fname in critical_files:
        if not os.path.exists(fname):
            continue
        try:
            # 1. Latest rolling backup (overwritten on each run)
            base, ext = os.path.splitext(fname)
            latest_bak = os.path.join(BACKUPS_DIR, f"{base}.backup{ext}")
            shutil.copy2(fname, latest_bak)

            # 2. Monthly snapshot archive (preserved across months)
            month_bak = os.path.join(BACKUPS_DIR, f"{base}_{month_str}{ext}")
            shutil.copy2(fname, month_bak)

            backed_up.append(fname)
        except Exception as e:
            print(f"[!] Backup error for {fname}: {e}")

    if backed_up:
        log_event("SUCCESS", "BackupManager", "backup_critical_logs", {"backed_up": backed_up})
    return backed_up
