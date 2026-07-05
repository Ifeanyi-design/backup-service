"""Backup Service configuration."""

import os


class Config:
    # PostgreSQL
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL environment variable is required")

    # Telegram
    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

    # Backup settings
    BACKUP_DIR = os.environ.get("BACKUP_DIR", "/tmp/backups")
    MAX_BACKUP_SIZE_MB = int(os.environ.get("MAX_BACKUP_SIZE_MB", "500"))
    RETENTION_DAYS = int(os.environ.get("RETENTION_DAYS", "30"))

    # API security
    API_KEY = os.environ.get("BACKUP_API_KEY", "")
    if not API_KEY:
        raise RuntimeError("BACKUP_API_KEY environment variable is required")

    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY", "backup-service-secret")
