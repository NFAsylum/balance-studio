# Balance Studio — backend (FastAPI). Deploy target: Fly.io.
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=2.4.1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

RUN pip install "poetry==${POETRY_VERSION}"

# Install only runtime deps first (cached layer); --no-root: we copy the source ourselves.
COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root --no-interaction

# App source (ui/, tests/, docs/ are excluded via .dockerignore)
COPY core ./core
COPY domains ./domains
COPY api ./api
COPY README.md ./

# File-based persistence (event log + snapshots) + optional disk cache live under /data,
# which Fly mounts as a volume. Prod cache normally uses Redis (CACHE_BACKEND=redis).
RUN mkdir -p /data/scenarios /data/cache
ENV SCENARIOS_DIR=/data/scenarios \
    CACHE_DIR=/data/cache \
    LLM_BACKEND=fake \
    CACHE_BACKEND=disk

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
