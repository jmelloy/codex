# ---- Frontend build stage ----
FROM node:24-slim AS frontend-builder
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Backend stage ----
FROM python:3.13-slim

ARG BUILD_VERSION=dev
LABEL org.opencontainers.image.version=${BUILD_VERSION}

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv

COPY backend/pyproject.toml ./
RUN uv pip install --system .

COPY backend/ .

# Copy built frontend assets
COPY --from=frontend-builder /frontend/dist /app/static

EXPOSE 8000

ENV PYTHONUNBUFFERED=1
ENV BUILD_VERSION=${BUILD_VERSION}

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["sh", "-c", "alembic upgrade head && python -m codex.main"]
