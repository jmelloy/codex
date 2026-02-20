FROM python:3.13-slim

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv

# Copy requirements first for better caching
COPY pyproject.toml ./
RUN uv pip install --system .

# Copy the entire backend directory
COPY . .

# Expose port
EXPOSE 8000

# Set Python to run in unbuffered mode for proper logging in Docker
ENV PYTHONUNBUFFERED=1

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run migrations then start the application via module entry point
CMD ["sh", "-c", "alembic upgrade head && python -m codex.main"]
