#!/bin/sh
export PYTHONPATH=/app
exec gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 2 wsgi:app
