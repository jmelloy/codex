FROM python:3.13-slim

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.9.27 /uv /uvx /bin/
ENV UV_NO_DEV=1

# Copy requirements first for better caching
COPY pyproject.toml ./
RUN uv sync --locked

# Copy the entire backend directory
COPY . .

# Expose port
EXPOSE 8000

# Set Python to run in unbuffered mode for proper logging in Docker
ENV PYTHONUNBUFFERED=1

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the application with production settings
CMD ["uvicorn", "codex.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--log-config", "/dev/null"]
