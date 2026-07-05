"""Backup Service API — Flask app with endpoints for backup/restore."""

import os
import functools

from flask import Flask, request, jsonify

from config import Config
from backup import create_backup, list_backups, cleanup_old_backups
from restore import restore_backup
from telegram import upload_backup_to_telegram, download_backup_from_telegram
from metadata import record_backup, mark_telegram_uploaded, get_metadata


app = Flask(__name__)
app.config.from_object(Config)


def require_api_key(f):
    """Decorator to require API key for endpoint access."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get("X-API-Key") or request.args.get("api_key")
        if api_key != Config.API_KEY:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint (no auth required)."""
    return jsonify({"status": "ok"})


@app.route("/backup", methods=["POST"])
@require_api_key
def backup():
    """Trigger a new backup."""
    include_telegram = request.json.get("include_telegram", True) if request.is_json else True

    result = create_backup()
    if not result["success"]:
        return jsonify({"error": result["error"]}), 500

    record_backup(result)

    telegram_result = None
    if include_telegram and Config.TELEGRAM_BOT_TOKEN:
        telegram_result = upload_backup_to_telegram(result["filepath"])
        if telegram_result.get("success"):
            mark_telegram_uploaded(result["filename"])

    cleanup_old_backups()

    return jsonify({
        "backup": result,
        "telegram": telegram_result,
    })


@app.route("/restore", methods=["POST"])
@require_api_key
def restore():
    """Restore from a backup."""
    data = request.get_json() or {}
    filepath = data.get("filepath")
    message_id = data.get("telegram_message_id")

    if not filepath and not message_id:
        return jsonify({"error": "Provide 'filepath' or 'telegram_message_id'"}), 400

    if message_id and not filepath:
        dl = download_backup_from_telegram(message_id)
        if not dl["success"]:
            return jsonify({"error": dl["error"]}), 500
        filepath = dl["filepath"]

    result = restore_backup(filepath)
    if not result["success"]:
        return jsonify({"error": result["error"]}), 500

    return jsonify(result)


@app.route("/status", methods=["GET"])
@require_api_key
def status():
    """Check backup service status."""
    backups = list_backups()
    metadata = get_metadata()

    return jsonify({
        "total_backups": len(backups),
        "latest_backup": backups[0] if backups else None,
        "telegram_configured": bool(Config.TELEGRAM_BOT_TOKEN),
        "metadata": metadata,
    })


@app.route("/list", methods=["GET"])
@require_api_key
def list_all():
    """List available backups."""
    backups = list_backups()
    return jsonify({"backups": backups})


def create_app():
    """Application factory."""
    return app
