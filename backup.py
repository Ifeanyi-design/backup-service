"""PostgreSQL backup logic using pg_dump."""

import os
import subprocess
import time
from datetime import datetime
from urllib.parse import urlparse

from config import Config


def parse_database_url(url):
    """Parse DATABASE_URL into components."""
    parsed = urlparse(url)
    return {
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "dbname": parsed.path.lstrip("/"),
        "user": parsed.username,
        "password": parsed.password,
    }


def create_backup(backup_dir=None):
    """Create a PostgreSQL SQL dump backup.

    Returns dict with backup metadata.
    """
    if backup_dir is None:
        backup_dir = Config.BACKUP_DIR

    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"maxcinema_backup_{timestamp}.sql"
    filepath = os.path.join(backup_dir, filename)

    db_info = parse_database_url(Config.DATABASE_URL)

    env = os.environ.copy()
    env["PGPASSWORD"] = db_info["password"]

    cmd = [
        "pg_dump",
        "-h", db_info["host"],
        "-p", str(db_info["port"]),
        "-U", db_info["user"],
        "-d", db_info["dbname"],
        "--no-owner",
        "--no-privileges",
        "-f", filepath,
    ]

    start_time = time.time()
    try:
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=3600,
        )
        duration = time.time() - start_time

        if result.returncode != 0:
            return {
                "success": False,
                "error": result.stderr,
                "duration": duration,
            }

        file_size = os.path.getsize(filepath)

        return {
            "success": True,
            "filepath": filepath,
            "filename": filename,
            "size_bytes": file_size,
            "size_mb": round(file_size / (1024 * 1024), 2),
            "duration": round(duration, 2),
            "timestamp": timestamp,
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Backup timed out after 1 hour",
            "duration": time.time() - start_time,
        }
    except FileNotFoundError:
        return {
            "success": False,
            "error": "pg_dump not found. Install postgresql-client.",
            "duration": time.time() - start_time,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "duration": time.time() - start_time,
        }


def list_backups(backup_dir=None):
    """List all backup files in the backup directory."""
    if backup_dir is None:
        backup_dir = Config.BACKUP_DIR

    if not os.path.exists(backup_dir):
        return []

    backups = []
    for f in sorted(os.listdir(backup_dir), reverse=True):
        if f.startswith("maxcinema_backup_") and f.endswith(".sql"):
            filepath = os.path.join(backup_dir, f)
            stat = os.stat(filepath)
            backups.append({
                "filename": f,
                "filepath": filepath,
                "size_bytes": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })

    return backups


def cleanup_old_backups(backup_dir=None, retention_days=None):
    """Remove backups older than retention_days."""
    if backup_dir is None:
        backup_dir = Config.BACKUP_DIR
    if retention_days is None:
        retention_days = Config.RETENTION_DAYS

    if not os.path.exists(backup_dir):
        return 0

    cutoff = time.time() - (retention_days * 86400)
    removed = 0

    for f in os.listdir(backup_dir):
        if f.startswith("maxcinema_backup_") and f.endswith(".sql"):
            filepath = os.path.join(backup_dir, f)
            if os.path.getmtime(filepath) < cutoff:
                os.remove(filepath)
                removed += 1

    return removed
