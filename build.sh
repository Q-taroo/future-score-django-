#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --noinput
test -f staticfiles/css/app.css
test -f staticfiles/js/vote.js
echo "collectstatic OK"
python manage.py migrate --noinput
echo "migrate OK"
python manage.py seed_predictions
python manage.py create_admin
