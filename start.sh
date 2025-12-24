#!/bin/sh
set -e

echo "Running  migrations..."
# python manage.py makemigrations
python manage.py migrate --noinput

echo "Migrations success..."

echo "Starting application..."
gunicorn backend_project.wsgi --bind 0.0.0.0:8000