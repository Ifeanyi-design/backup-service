"""Backup metadata tracking."""

import json
import os
import time
from datetime import datetime

from config import Config


METADATA_FILE = "backup_metadata.json"


def _get_metadata_path():
    """Get path to metadata file."""
    return os.path.join(Config.BACKUP_DIR, METADATA_FILE)


def _load_metadata():
    """Load metadata from file."""
    path = _get_metadata_path()
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {"backups": []}


def _save_metadata(data):
    """Save metadata to file."""
    os.makedirs(Config.BACKUP_DIR, exist_ok=True)
    with open(_get_metadata_path(), "w") as f:
        json.dump(data, f, indent=2)


def record_backup(backup_info):
    """Record a backup in metadata."""
    data = _load_metadata()
    data["backups"].append({
        "filename": backup_info.get("filename"),
        "size_bytes": backup_info.get("size_bytes"),
        "size_mb": backup_info.get("size_mb"),
        "duration": backup_info.get("duration"),
        "timestamp": backup_info.get("timestamp"),
        "created_at": datetime.utcnow().isoformat(),
        "uploaded_to_telegram": False,
    })
    _save_metadata(data)


def mark_telegram_uploaded(filename):
    """Mark a backup as uploaded to Telegram."""
    data = _load_metadata()
    for b in data["backups"]:
        if b["filename"] == filename:
            b["uploaded_to_telegram"] = True
            break
    _save_metadata(data)


def get_metadata():
    """Get all backup metadata."""
    return _load_metadata()


def get_recent_backups(limit=10):
    """Get most recent backups from metadata."""
    data = _load_metadata()
    return data["backups"][:limit]
