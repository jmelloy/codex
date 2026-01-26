# Build stage
FROM node:25-slim AS builder

WORKDIR /app

# Build argument for API URL (baked into the build)
ARG VITE_API_BASE_URL=/api

# Copy package files first for better caching
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production=false

# Copy source code
COPY . ./

# Set environment variable for build
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

# Build application
RUN npm run build

# Production stage
FROM nginx:alpine

# Add non-root user for nginx
RUN addgroup -g 1000 -S codex && \
    adduser -u 1000 -S codex -G codex

# Copy built files
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Set proper permissions
RUN chown -R codex:codex /usr/share/nginx/html && \
    chown -R codex:codex /var/cache/nginx && \
    chown -R codex:codex /var/log/nginx && \
    touch /var/run/nginx.pid && \
    chown -R codex:codex /var/run/nginx.pid

# Security: remove server version
RUN sed -i 's/^user .*/user codex;/' /etc/nginx/nginx.conf

EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost:80 || exit 1

CMD ["nginx", "-g", "daemon off;"]
