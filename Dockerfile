# Stage 1: Base build stage
FROM python:3.13-slim AS builder

RUN mkdir /app

WORKDIR /app

ENV ENV=production

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=backend_project.settings.${ENV}

RUN pip install --upgrade pip

COPY requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Production stage

FROM python:3.13-slim

COPY --from=builder /usr/local/lib/python3.13/site-packages/ /usr/local/lib/python3.13/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

RUN useradd -m -r appuser && \
   mkdir /app && \
   chown -R appuser /app

WORKDIR /app

COPY --chown=appuser:appuser . .

ENV ENV=production

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=backend_project.settings.${ENV}

USER appuser

EXPOSE 8000

CMD ["sh", "-c", "python manage.py makemigrations && python manage.py migrate --noinput && gunicorn backend_project.wsgi --bind 0.0.0.0:8000"]