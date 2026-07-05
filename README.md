# MaxCinema Backup Service

Independent PostgreSQL backup/restore service with Telegram integration.

## Features

- Automated PostgreSQL backups via `pg_dump`
- Restore from local backup or Telegram
- Telegram channel upload for offsite storage
- Configurable retention policy
- REST API for triggering backups/restores

## Setup

### Environment Variables

```bash
DATABASE_URL=postgresql://...        # Required
BACKUP_API_KEY=your-secret-key       # Required
TELEGRAM_BOT_TOKEN=123:ABC           # Optional (for Telegram upload)
TELEGRAM_CHAT_ID=-100123456          # Optional
BACKUP_DIR=/tmp/backups              # Optional (default: /tmp/backups)
RETENTION_DAYS=30                    # Optional (default: 30)
```

### Run Locally

```bash
pip install -r requirements.txt
python -m backup_service.app
```

### Run with Docker

```bash
docker build -t maxcinema-backup .
docker run -p 8080:8080 --env-file .env maxcinema-backup
```

## API Endpoints

All endpoints require `X-API-Key` header except `/health`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/backup` | Trigger backup |
| POST | `/restore` | Restore from backup |
| GET | `/status` | Backup service status |
| GET | `/list` | List available backups |

### Example: Trigger Backup

```bash
curl -X POST http://localhost:8080/backup \
  -H "X-API-Key: your-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"include_telegram": true}'
```

### Example: Restore

```bash
curl -X POST http://localhost:8080/restore \
  -H "X-API-Key: your-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"filepath": "/tmp/backups/maxcinema_backup_20260705.sql"}'
```

## Architecture

```
backup_service/
├── __init__.py       # Package init
├── app.py            # Flask API endpoints
├── config.py         # Configuration
├── backup.py         # PostgreSQL backup logic
├── restore.py        # PostgreSQL restore logic
├── telegram.py       # Telegram upload/download
├── metadata.py       # Backup metadata tracking
├── requirements.txt  # Dependencies
└── Dockerfile        # Container build
```

## Notes

- Uses `pg_dump` / `psql` (requires `postgresql-client` in PATH)
- Backups are SQL format (not custom format) for portability
- Telegram upload has 50MB file size limit (configurable)
- Old backups auto-cleaned after RETENTION_DAYS
