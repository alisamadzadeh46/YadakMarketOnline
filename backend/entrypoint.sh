#!/bin/sh
# Resilient startup for the web service.
#
# Docker Desktop's embedded DNS can briefly be unavailable in the first moment
# after a container starts, which makes the very first connection to "postgres"
# fail with a name-resolution error. We retry until the database is reachable
# before running migrations, then hand off to the given command.
set -e

echo "Waiting for the database to become reachable..."
until python -c "import os, psycopg; psycopg.connect(os.environ['DATABASE_URL']).close()" 2>/dev/null; do
  echo "  database not ready yet — retrying in 2s"
  sleep 2
done
echo "Database is reachable."

python manage.py migrate --noinput

# Static files are only needed when serving through gunicorn/WhiteNoise. The dev
# runserver serves admin assets itself, so we skip collectstatic unless asked.
if [ "$COLLECT_STATIC" = "1" ]; then
  python manage.py collectstatic --noinput
fi

# Replace the shell with the container's main process (e.g. runserver/gunicorn).
exec "$@"
