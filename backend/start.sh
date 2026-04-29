#!/usr/bin/env bash
set -o errexit

# Start Celery worker + beat in background
celery -A config worker -l info -B &

# Start Gunicorn in foreground
gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
