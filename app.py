"""Backup Service API — Flask app with endpoints for backup/restore."""

import functools
import logging
import subprocess

from flask import Flask, request, jsonify

from config import Config
from backup import create_backup, list_backups, cleanup_old_backups
from restore import restore_backup
from telegram import upload_backup_to_telegram, download_backup_from_telegram
from metadata import record_backup, mark_telegram_uploaded, get_metadata

# ---------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

logger = logging.getLogger("backup-service")

# ---------------------------------------------------------------------

app = Flask(__name__)
app.config.from_object(Config)

logger.info("Backup service starting...")


def require_api_key(f):
    """Decorator to require API key for endpoint access."""

    @functools.wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get("X-API-Key") or request.args.get("api_key")

        if api_key != Config.API_KEY:
            logger.warning("Unauthorized request")
            return jsonify({"error": "Unauthorized"}), 401

        return f(*args, **kwargs)

    return decorated


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok"})


@app.route("/version", methods=["GET"])
def version():
    """Show installed PostgreSQL tools."""

    try:
        result = subprocess.run(
            ["pg_dump", "--version"],
            capture_output=True,
            text=True,
        )

        return jsonify({
            "pg_dump": result.stdout.strip(),
            "return_code": result.returncode,
        })

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


@app.route("/backup", methods=["POST"])
@require_api_key
def backup():
    """Trigger a new backup."""

    include_telegram = (
        request.json.get("include_telegram", True)
        if request.is_json
        else True
    )

    logger.info("========== BACKUP START ==========")
    logger.info("Telegram upload enabled: %s", include_telegram)

    logger.info("Creating PostgreSQL backup...")

    result = create_backup()

    logger.info("Backup result: %s", result)

    if not result["success"]:
        logger.error("Backup FAILED")
        logger.error(result["error"])

        return jsonify({
            "error": result["error"]
        }), 500

    logger.info("Recording backup metadata...")
    record_backup(result)

    telegram_result = None

    if include_telegram:

        if Config.TELEGRAM_BOT_TOKEN:
            logger.info("Uploading backup to Telegram...")

            telegram_result = upload_backup_to_telegram(
                result["filepath"]
            )

            logger.info("Telegram response: %s", telegram_result)

            if telegram_result.get("success"):
                logger.info("Telegram upload successful")
                mark_telegram_uploaded(result["filename"])
            else:
                logger.error("Telegram upload failed")

        else:
            logger.warning("Telegram token not configured")

    else:
        logger.info("Telegram upload skipped by request")

    removed = cleanup_old_backups()

    logger.info("Old backups removed: %s", removed)
    logger.info("========== BACKUP FINISHED ==========")

    return jsonify({
        "backup": result,
        "telegram": telegram_result,
    })


@app.route("/restore", methods=["POST"])
@require_api_key
def restore():
    """Restore a PostgreSQL backup."""

    logger.info("Restore requested")

    data = request.get_json() or {}

    filepath = data.get("filepath")
    message_id = data.get("telegram_message_id")

    if not filepath and not message_id:
        return jsonify({
            "error": "Provide 'filepath' or 'telegram_message_id'"
        }), 400

    if message_id and not filepath:

        logger.info("Downloading backup from Telegram...")

        dl = download_backup_from_telegram(message_id)

        logger.info("Telegram download result: %s", dl)

        if not dl["success"]:
            return jsonify({
                "error": dl["error"]
            }), 500

        filepath = dl["filepath"]

    logger.info("Restoring backup: %s", filepath)

    result = restore_backup(filepath)

    logger.info("Restore result: %s", result)

    if not result["success"]:
        logger.error("Restore failed")

        return jsonify({
            "error": result["error"]
        }), 500

    logger.info("Restore completed successfully")

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
    """List backups."""

    return jsonify({
        "backups": list_backups()
    })


def create_app():
    """Application factory."""
    return app