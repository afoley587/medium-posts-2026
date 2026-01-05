FROM python:3.12-slim AS builder

ENV POETRY_NO_INTERACTION=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache \
    POETRY_HOME="/opt/poetry" \
    POETRY_VERSION=2.1.3

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install poetry==$POETRY_VERSION

WORKDIR /app

COPY pyproject.toml poetry.lock* ./

RUN pip install poetry-plugin-export
RUN poetry export -f requirements.txt \
    --output requirements.txt \
    --without-hashes \
    --without dev

FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

RUN groupadd -r -g 1001 appuser && \
    useradd -r -u 1001 -g appuser -m -d /home/appuser -s /bin/bash appuser

WORKDIR /app

COPY --from=builder /app/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser fastapi_otel/ .

USER appuser

EXPOSE 8000

LABEL \
    org.opencontainers.image.title="FastAPI OTEL" \
    org.opencontainers.image.description="FastAPI-based OTEL Example Application" \
    org.opencontainers.image.vendor="DevOps Team" \
    security.scan="enabled"

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

CMD ["python", "fast.py"]
