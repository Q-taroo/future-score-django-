# Single-stage build: Django + gunicorn. No frontend build step at all —
# templates are server-rendered and static/ is a hand-written, dependency-
# free CSS/JS tree (see static/css/app.css for why: no CDN, no Node).
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# psycopg[binary] ships its own libpq, so no build-essential/libpq-dev
# is required here.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
