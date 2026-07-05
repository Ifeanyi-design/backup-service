"""PostgreSQL restore logic using psql."""

import os
import subprocess
import time

from config import Config
from backup import parse_database_url


def restore_backup(filepath):
    """Restore a PostgreSQL backup from a SQL dump file.

    Returns dict with restore metadata.
    """
    if not os.path.exists(filepath):
        return {
            "success": False,
            "error": f"Backup file not found: {filepath}",
        }

    db_info = parse_database_url(Config.DATABASE_URL)

    env = os.environ.copy()
    env["PGPASSWORD"] = db_info["password"]

    cmd = [
        "psql",
        "-h", db_info["host"],
        "-p", str(db_info["port"]),
        "-U", db_info["user"],
        "-d", db_info["dbname"],
        "-f", filepath,
        "--single-transaction",
    ]

    start_time = time.time()
    try:
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=7200,
        )
        duration = time.time() - start_time

        if result.returncode != 0:
            return {
                "success": False,
                "error": result.stderr,
                "duration": duration,
            }

        return {
            "success": True,
            "filepath": filepath,
            "duration": round(duration, 2),
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Restore timed out after 2 hours",
            "duration": time.time() - start_time,
        }
    except FileNotFoundError:
        return {
            "success": False,
            "error": "psql not found. Install postgresql-client.",
            "duration": time.time() - start_time,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "duration": time.time() - start_time,
        }
