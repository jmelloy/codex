# Build stage
FROM node:25-slim AS builder
WORKDIR /app

# Build arguments
ARG VITE_API_BASE_URL=/api
ARG PLUGINS_DIR=/plugins

# Install pnpm via npm
RUN npm install -g pnpm

# Copy lockfile and package.json
COPY pnpm-lock.yaml package.json ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source code
COPY . ./

# Create plugins directory
RUN mkdir -p /plugins

# Set environment variables for build
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_PLUGINS_DIR=${PLUGINS_DIR}

# Build application
RUN pnpm build

# Production stage (unchanged)
FROM nginx:alpine

RUN addgroup -g 1000 -S codex && \
    adduser -u 1000 -S codex -G codex

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

RUN chown -R codex:codex /usr/share/nginx/html && \
    chown -R codex:codex /var/cache/nginx && \
    chown -R codex:codex /var/log/nginx && \
    touch /var/run/nginx.pid && \
    chown -R codex:codex /var/run/nginx.pid

RUN sed -i 's/^user .*/user codex;/' /etc/nginx/nginx.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget -q --spider http://127.0.0.1:80 || exit 1

CMD ["nginx", "-g", "daemon off;"]