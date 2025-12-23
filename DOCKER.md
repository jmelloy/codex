# Docker Deployment Guide

This guide explains how to deploy Codex using Docker and Docker Compose for both development and production environments.

## Prerequisites

- Docker Engine 20.10 or later
- Docker Compose V2 or later
- At least 2GB of available disk space
- Port 80 and 8765 available (or configure different ports)

## Quick Start (Production)

1. **Clone the repository**

   ```bash
   git clone https://github.com/jmelloy/codex
   cd codex
   ```

2. **Validate configuration (optional but recommended)**

   ```bash
   ./validate-docker.sh
   ```

3. **Configure environment (optional)**

   ```bash
   cp .env.example .env
   # Edit .env file with your configuration
   ```

4. **Start the services**

   ```bash
   docker compose -f docker-compose.prod.yml up -d
   ```

5. **Access the application**

   - Frontend: http://localhost
   - API: http://localhost:8765
   - API Documentation: http://localhost:8765/docs

6. **Check service health**
   ```bash
   docker compose -f docker-compose.prod.yml ps
   docker compose -f docker-compose.prod.yml logs
   ```

## Production Deployment

### Architecture

The production setup consists of:

- **Backend**: Python FastAPI application running on port 8765
- **Frontend**: Nginx serving the built Vue.js application on port 80
- **Persistent Storage**: Docker volume for workspace data

### Configuration

#### Environment Variables

Create a `.env` file based on `.env.example`:

```bash
# Backend Configuration
CODEX_WORKSPACE_PATH=/data/workspace
DEBUG=false

# Server Configuration
BACKEND_PORT=8765
FRONTEND_PORT=80
```

#### Custom Ports

To use different ports, modify `docker-compose.prod.yml`:

```yaml
services:
  backend:
    ports:
      - "8080:8765" # Map to port 8080 instead of 8765

  frontend:
    ports:
      - "8080:80" # Map to port 8080 instead of 80
```

Or use environment variables in your command:

```bash
BACKEND_PORT=8080 FRONTEND_PORT=8080 docker compose -f docker-compose.prod.yml up -d
```

### Managing the Deployment

#### Start Services

```bash
docker compose -f docker-compose.prod.yml up -d
```

#### Stop Services

```bash
docker compose -f docker-compose.prod.yml down
```

#### View Logs

```bash
# All services
docker compose -f docker-compose.prod.yml logs -f

# Specific service
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f frontend
```

#### Restart Services

```bash
# Restart all
docker compose -f docker-compose.prod.yml restart

# Restart specific service
docker compose -f docker-compose.prod.yml restart backend
```

#### Update Application

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker compose -f docker-compose.prod.yml up -d --build
```

### Data Persistence

Workspace data is stored in a named Docker volume `codex_workspace`. This persists across container restarts and updates.

#### Backup Workspace Data

```bash
# Create a backup
docker run --rm \
  -v codex_workspace:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/codex-workspace-$(date +%Y%m%d-%H%M%S).tar.gz -C /data .
```

#### Restore Workspace Data

```bash
# Restore from backup
docker run --rm \
  -v codex_workspace:/data \
  -v $(pwd)/backups:/backup \
  alpine tar xzf /backup/codex-workspace-YYYYMMDD-HHMMSS.tar.gz -C /data
```

#### View Volume Location

```bash
docker volume inspect codex_workspace
```

### Health Checks

Both services include health checks:

- **Backend**: Checks `/health` endpoint using Python's built-in `http.client` every 30 seconds
- **Frontend**: Checks nginx status using `wget` every 30 seconds

View health status:

```bash
docker compose -f docker-compose.prod.yml ps
```

Unhealthy containers will automatically restart.

**Customizing Health Checks**

The default health checks use built-in tools to avoid external dependencies. However, you can simplify them if needed.

**Simpler Backend Health Check Options:**

1. **Install curl in Dockerfile** (recommended for production):

   ```dockerfile
   # Add to Dockerfile after system dependencies
   RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
   ```

   Then in docker-compose.prod.yml:

   ```yaml
   healthcheck:
     test: ["CMD", "curl", "-f", "http://localhost:8765/health"]
   ```

2. **Use a health check script**:
   Create `healthcheck.py` in your project:
   ```python
   import http.client
   h = http.client.HTTPConnection('localhost:8765')
   h.request('GET', '/health')
   exit(0 if h.getresponse().status == 200 else 1)
   ```
   Then in docker-compose.prod.yml:
   ```yaml
   healthcheck:
     test: ["CMD", "python", "/app/healthcheck.py"]
   ```

**Frontend Health Check Alternatives:**

```yaml
# Using curl (requires adding curl to nginx image)
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost/"]

# Check nginx configuration and process
healthcheck:
  test: ["CMD-SHELL", "nginx -t && pgrep nginx"]
```

## Development Deployment

For development with hot-reload:

```bash
docker compose up -d
```

This uses `docker-compose.yml` which includes:

- Source code volume mounts for hot-reload
- Development server with `--reload` flag
- Frontend with Vite dev server
- Debug logging enabled

Access the development environment:

- Frontend: http://localhost:5174
- Backend API: http://localhost:8765
- API Documentation: http://localhost:8765/docs

## Troubleshooting

### Services Won't Start

1. **Check port availability**

   ```bash
   # Check if ports are in use
   lsof -i :80
   lsof -i :8765
   ```

2. **Check logs**

   ```bash
   docker compose -f docker-compose.prod.yml logs
   ```

3. **Verify Docker resources**
   ```bash
   docker system df
   docker system prune  # Clean up if needed
   ```

### Frontend Can't Connect to Backend

1. **Verify backend is healthy**

   ```bash
   docker compose -f docker-compose.prod.yml ps
   curl http://localhost:8765/health
   ```

2. **Check nginx configuration**

   ```bash
   docker compose -f docker-compose.prod.yml exec frontend cat /etc/nginx/conf.d/default.conf
   ```

3. **View frontend logs**
   ```bash
   docker compose -f docker-compose.prod.yml logs frontend
   ```

### Database Issues

If you see database-related errors:

```bash
# Stop services
docker compose -f docker-compose.prod.yml down

# Remove volume (WARNING: This deletes all data)
docker volume rm codex_workspace

# Restart services (will initialize fresh database)
docker compose -f docker-compose.prod.yml up -d
```

### Build Issues

#### SSL Certificate Errors

If you encounter SSL certificate errors during build (common in CI/CD environments with corporate proxies):

```bash
# Option 1: Configure pip to trust your certificates
# Add to Dockerfile or build args
docker compose -f docker-compose.prod.yml build --build-arg PIP_TRUSTED_HOST=pypi.org

# Option 2: Use system certificates
# Mount CA certificates as a build secret (Docker Buildx)
docker buildx build --secret id=cacert,src=/etc/ssl/certs/ca-certificates.crt .

# Option 3: Temporarily disable SSL verification (NOT recommended for production)
# Only use in controlled CI/CD environments
export DOCKER_BUILDKIT=1
docker compose -f docker-compose.prod.yml build --build-arg PIP_NO_VERIFY=1
```

#### Network Issues During Build

If builds fail due to network issues:

```bash
# Clean Docker build cache and retry
docker builder prune -a
docker compose -f docker-compose.prod.yml build --no-cache
```

### Permission Issues

If you encounter permission errors with volumes:

```bash
# Check volume permissions
docker compose -f docker-compose.prod.yml exec backend ls -la /data/workspace

# Fix ownership if needed
docker compose -f docker-compose.prod.yml exec backend chown -R nobody:nogroup /data/workspace
```

## Advanced Configuration

### Using External Database

To use an external PostgreSQL database instead of SQLite:

1. Update `.env`:

   ```bash
   DATABASE_URL=postgresql://user:password@host:5432/codex
   ```

2. Update backend environment in `docker-compose.prod.yml`:
   ```yaml
   environment:
     - DATABASE_URL=${DATABASE_URL}
   ```

### Reverse Proxy Setup

If running behind a reverse proxy (nginx, Traefik, etc.):

1. **Don't expose ports directly**

   ```yaml
   services:
     frontend:
       # Remove or comment out ports
       # ports:
       #   - "80:80"
   ```

2. **Configure proxy headers**
   Ensure your reverse proxy passes these headers:

   - `X-Real-IP`
   - `X-Forwarded-For`
   - `X-Forwarded-Proto`
   - `Host`

3. **Example nginx reverse proxy config**
   ```nginx
   server {
       listen 80;
       server_name example.com;

       location / {
           proxy_pass http://localhost:80;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

### SSL/TLS Configuration

For production, use a reverse proxy with SSL/TLS:

1. **Using Let's Encrypt with Certbot**

   ```bash
   certbot --nginx -d example.com
   ```

2. **Using Docker with Traefik**
   See [Traefik documentation](https://doc.traefik.io/traefik/) for automatic SSL with Let's Encrypt

### Resource Limits

To limit resource usage, add to `docker-compose.prod.yml`:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 1G
        reservations:
          memory: 512M

  frontend:
    deploy:
      resources:
        limits:
          cpus: "0.5"
          memory: 512M
        reservations:
          memory: 256M
```

## Monitoring

### View Container Stats

```bash
docker stats
```

### Export Logs to File

```bash
docker compose -f docker-compose.prod.yml logs > codex-logs.txt
```

### Integration with Monitoring Tools

For production monitoring, consider integrating with:

- **Prometheus**: For metrics collection
- **Grafana**: For visualization
- **ELK Stack**: For log aggregation
- **Sentry**: For error tracking

## Security Considerations

1. **Change default ports** if exposing to the internet
2. **Use strong secrets** for API keys and database passwords
3. **Keep containers updated**: Regularly rebuild images
4. **Limit network exposure**: Use firewall rules
5. **Enable authentication**: Add authentication layer if needed
6. **Regular backups**: Automate workspace backups
7. **Use HTTPS**: Always use SSL/TLS in production

## Support

For issues and questions:

- GitHub Issues: https://github.com/jmelloy/codex/issues
- Documentation: See README.md
- API Docs: http://localhost:8765/docs (when running)
