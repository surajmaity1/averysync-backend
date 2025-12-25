#!/bin/sh
set -e

echo "Running  migrations..."

echo "Running manage.py makemigrations"

python manage.py makemigrations

echo "Running python manage.py migrate --noinput"


