# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
    nodejs \
    npm \
    default-jdk-headless \
  && rm -rf /var/lib/apt/lists/*

RUN npm install -g ts-node typescript

ENV POETRY_HOME="/opt/poetry" \
    POETRY_VERSION=1.8.3 \
    PIP_NO_CACHE_DIR=1
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /opt/poetry/bin/poetry /usr/local/bin/poetry

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --only main

COPY app ./app
COPY workflow ./workflow
COPY questions.yaml ./questions.yaml
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
