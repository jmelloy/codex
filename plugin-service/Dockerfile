# Stage 1: Build plugin Vue components
FROM node:25-slim AS plugin-builder
WORKDIR /plugins

# Copy plugin source and build tooling
COPY plugins/package.json plugins/package-lock.json plugins/build.ts plugins/tsconfig.json ./

# Install build dependencies
RUN npm ci

# Copy all plugin source directories (manifests, Vue components, styles, etc.)
COPY plugins/ ./

# Build plugin Vue components → dist/ directories + plugins.json
RUN npx tsx build.ts

# Stage 2: Python service
FROM python:3.11-slim

ARG BUILD_VERSION=dev
LABEL org.opencontainers.image.version=${BUILD_VERSION}

WORKDIR /app

# Install the service package
COPY plugin-service/pyproject.toml ./
RUN pip install --no-cache-dir .

# Copy service code
COPY plugin-service/codex_plugin_service ./codex_plugin_service

# Copy built plugins from the builder stage (includes dist/ and manifests)
COPY --from=plugin-builder /plugins /app/plugins

ENV PLUGIN_SERVICE_DIR=/app/plugins
ENV BUILD_VERSION=${BUILD_VERSION}

EXPOSE 8090

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8090/health')" || exit 1

CMD ["python", "-m", "codex_plugin_service.main"]
