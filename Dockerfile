FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY pyproject.toml .

RUN pip install -e .
COPY codex ./codex

# Expose the API port
EXPOSE 8765

# Run the API server
CMD ["uvicorn", "codex.api.main:app", "--host", "0.0.0.0", "--port", "8765"]
