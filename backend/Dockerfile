# syntax=docker/dockerfile:1

# ---- Base image -------------------------------------------------------------
# Slim Python 3.13 keeps the image small while giving us a modern interpreter.
FROM python:3.13-slim AS base

# Environment: no .pyc files, unbuffered stdout so container logs stream live.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System packages required to build/run psycopg and Pillow.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libjpeg-dev \
        zlib1g-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first so Docker can cache this layer across code changes.
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the application source.
COPY . .

# Create an unprivileged user; never run the app as root.
RUN adduser --disabled-password --gecos "" appuser \
    && mkdir -p /app/staticfiles /app/media \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Default command is overridden per-service in docker-compose.
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
