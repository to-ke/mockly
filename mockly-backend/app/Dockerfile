# syntax=docker/dockerfile:1
FROM python:3.11-slim

# 1) OS deps you need (compilers, Java for /api/execute Java, Node/TS, etc.)
RUN apt-get update && apt-get install -y \
    build-essential openjdk-17-jre-headless openjdk-17-jdk-headless \
    nodejs npm g++ \
  && rm -rf /var/lib/apt/lists/*

# 2) Optional: TypeScript runtime for executing TS
RUN npm install -g ts-node typescript

# 3) Install Poetry (no venvs; install to system site-packages in the container)
ENV POETRY_HOME="/opt/poetry" \
    POETRY_VERSION=1.8.3 \
    PIP_NO_CACHE_DIR=1
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /opt/poetry/bin/poetry /usr/local/bin/poetry

WORKDIR /app

# 4) Copy only dependency manifests first for better Docker layer caching
COPY pyproject.toml poetry.lock ./

# 5) Install project deps into the image’s global interpreter (no virtualenv)
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --only main

# 6) Copy the application code last (so edits don’t bust the deps cache)
COPY app ./app

# 7) Runtime env
ENV USE_FIREJAIL=0

EXPOSE 8000

# 8) Start FastAPI with Uvicorn (bind 0.0.0.0 for Docker networking)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
