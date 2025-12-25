# Use an official Python runtime as a parent image
FROM python:3.14-slim

ENV ENV=production

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=backend_project.settings.${ENV}

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

ARG UID=10001

RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

# RUN --mount=type=cache,id=pip_cache,target=/root/.cache/pip \
#     --mount=type=bind,source=requirements.txt,target=requirements.txt \

COPY . .

RUN chmod +x start.sh

RUN python -m pip install -r requirements.txt

USER appuser


EXPOSE 8000

CMD ["./start.sh"]