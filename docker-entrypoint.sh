#!/usr/bin/env sh
set -eu

python manage.py migrate --noinput
python manage.py seed_predictions
python manage.py create_admin
exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3
