"""Telegram integration for backup upload/download."""

import os
import requests
from datetime import datetime

from config import Config


def _get_api_base():
    """Get Telegram Bot API base URL."""
    token = Config.TELEGRAM_BOT_TOKEN
    if not token:
        return None
    return f"https://api.telegram.org/bot{token}"


def upload_backup_to_telegram(filepath, caption=None):
    """Upload a backup file to Telegram channel.

    Returns dict with upload status.
    """
    api_base = _get_api_base()
    chat_id = Config.TELEGRAM_CHAT_ID

    if not api_base:
        return {"success": False, "error": "TELEGRAM_BOT_TOKEN not configured"}
    if not chat_id:
        return {"success": False, "error": "TELEGRAM_CHAT_ID not configured"}

    if not os.path.exists(filepath):
        return {"success": False, "error": f"File not found: {filepath}"}

    filename = os.path.basename(filepath)
    file_size_mb = os.path.getsize(filepath) / (1024 * 1024)

    if file_size_mb > Config.MAX_BACKUP_SIZE_MB:
        return {
            "success": False,
            "error": f"File too large: {file_size_mb}MB (max: {Config.MAX_BACKUP_SIZE_MB}MB)",
        }

    if caption is None:
        caption = (
            f"MaxCinema Backup\n"
            f"Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n"
            f"Size: {file_size_mb:.1f} MB"
        )

    try:
        with open(filepath, "rb") as f:
            resp = requests.post(
                f"{api_base}/sendDocument",
                data={"chat_id": chat_id, "caption": caption},
                files={"document": (filename, f, "application/octet-stream")},
                timeout=300,
            )

        if resp.status_code == 200:
            data = resp.json()
            if data.get("ok"):
                return {
                    "success": True,
                    "message_id": data["result"]["message_id"],
                    "filename": filename,
                }

        return {"success": False, "error": resp.text}

    except Exception as e:
        return {"success": False, "error": str(e)}


def download_backup_from_telegram(message_id, download_dir=None):
    """Download a backup file from Telegram by message ID.

    Returns dict with download status.
    """
    api_base = _get_api_base()

    if not api_base:
        return {"success": False, "error": "TELEGRAM_BOT_TOKEN not configured"}

    if download_dir is None:
        download_dir = Config.BACKUP_DIR

    os.makedirs(download_dir, exist_ok=True)

    try:
        resp = requests.get(
            f"{api_base}/getFile",
            params={"file_id": message_id},
            timeout=30,
        )

        if resp.status_code != 200 or not resp.json().get("ok"):
            return {"success": False, "error": "Failed to get file info from Telegram"}

        file_path = resp.json()["result"]["file_path"]
        filename = os.path.basename(file_path)
        download_path = os.path.join(download_dir, filename)

        file_resp = requests.get(
            f"https://api.telegram.org/file/bot{Config.TELEGRAM_BOT_TOKEN}/{file_path}",
            timeout=300,
        )

        if file_resp.status_code != 200:
            return {"success": False, "error": "Failed to download file from Telegram"}

        with open(download_path, "wb") as f:
            f.write(file_resp.content)

        return {
            "success": True,
            "filepath": download_path,
            "filename": filename,
            "size_bytes": len(file_resp.content),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
