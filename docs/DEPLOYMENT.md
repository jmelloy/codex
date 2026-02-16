# Codex Deployment Guide

**Version:** 1.0 | **Date:** 2026-02-16

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Local Development Setup](#local-development-setup)
4. [Docker Development](#docker-development)
5. [Production Deployment](#production-deployment)
6. [Cloud Deployments](#cloud-deployments)
7. [Kubernetes Deployment](#kubernetes-deployment)
8. [Security Configuration](#security-configuration)
9. [Monitoring & Maintenance](#monitoring--maintenance)
10. [Troubleshooting](#troubleshooting)
11. [Backup & Recovery](#backup--recovery)

## Overview

This guide covers deploying Codex in various environments, from local development to production cloud deployments. Codex supports:

- **Local Development**: Native Python + Node.js
- **Docker Development**: Docker Compose for quick start
- **Production**: Dockerized deployment with nginx
- **Cloud**: AWS, GCP, Azure, DigitalOcean
- **Kubernetes**: Scalable orchestration

## Prerequisites

### Minimum Requirements

**Hardware:**
- CPU: 2 cores
- RAM: 4 GB
- Disk: 20 GB (+ space for notebooks)

**Software:**
- Python 3.13 or higher
- Node.js 24 or higher
- Docker 24+ and Docker Compose (for containerized deployments)

### Recommended Production Requirements

**Hardware:**
- CPU: 4 cores
- RAM: 8 GB
- Disk: SSD with 100+ GB

**Software:**
- Ubuntu 22.04 LTS or Debian 12
- Docker 24+ with Docker Compose v2
- Nginx 1.24+ (for reverse proxy)
- PostgreSQL 15+ (optional, for scaling)

## Local Development Setup

### 1. Clone Repository

```bash
git clone https://github.com/jmelloy/codex.git
cd codex
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Create environment file
cp ../.env.example ../.env
# Edit .env and set SECRET_KEY (generate with: python -c "import secrets; print(secrets.token_hex(32))")

# Initialize database
alembic upgrade head

# Start backend server
python -m codex.main
# Or with uvicorn:
uvicorn codex.main:app --reload --port 8000
```

**Backend will be available at:** `http://localhost:8000`
**API documentation:** `http://localhost:8000/docs`

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Create environment file (optional)
cp .env.example .env
# Edit if backend is not at http://localhost:8000

# Start development server
npm run dev
```

**Frontend will be available at:** `http://localhost:5173`

### 4. Load Test Data (Optional)

```bash
cd backend
python -m codex.scripts.seed_test_data
```

This creates three test users:
- `demo` / `demo123456`
- `testuser` / `testpass123`
- `scientist` / `lab123456`

See [TEST_CREDENTIALS.md](../TEST_CREDENTIALS.md) for details.

### 5. Verify Installation

```bash
# Test backend
curl http://localhost:8000/health

# Test frontend
open http://localhost:5173
```

## Docker Development

### Quick Start

```bash
# Copy environment file
cp .env.example .env

# Generate secret key
python3 -c "import secrets; print(secrets.token_hex(32))"
# Add to .env: SECRET_KEY=<generated_key>

# Start all services
docker compose up -d

# View logs
docker compose logs -f

# Access services
# Frontend: http://localhost:8065
# Backend: http://localhost:8765
# API Docs: http://localhost:8765/docs
```

### Service Management

```bash
# Stop services
docker compose down

# Rebuild after code changes
docker compose build
docker compose up -d

# View service status
docker compose ps

# Execute commands in containers
docker compose exec backend python -m codex.scripts.seed_test_data
docker compose exec backend alembic upgrade head
```

### Data Persistence

Data is stored in Docker volumes:
```bash
# List volumes
docker volume ls | grep codex

# Backup data
docker compose exec backend tar czf /tmp/data-backup.tar.gz /app/data
docker compose cp backend:/tmp/data-backup.tar.gz ./backups/

# Restore data
docker compose cp ./backups/data-backup.tar.gz backend:/tmp/
docker compose exec backend tar xzf /tmp/data-backup.tar.gz -C /app/data
```

## Production Deployment

### Architecture Overview

```
Internet
   ↓
[SSL Termination] (Let's Encrypt/Nginx)
   ↓
[Nginx Reverse Proxy]
   ├─→ Frontend (Static Files)
   └─→ Backend (FastAPI)
         ├─→ System DB (SQLite/PostgreSQL)
         ├─→ Notebook DBs (SQLite)
         └─→ Filesystem Storage
```

### 1. Prepare Server

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose-plugin

# Create application directory
sudo mkdir -p /opt/codex
sudo chown $USER:$USER /opt/codex
cd /opt/codex
```

### 2. Clone and Configure

```bash
# Clone repository
git clone https://github.com/jmelloy/codex.git .

# Create production environment file
cat > .env << EOF
# Security
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# Database
DATABASE_URL=sqlite:///./data/codex_system.db

# Server
DEBUG=false
LOG_LEVEL=INFO
LOG_FORMAT=json

# Paths
CODEX_PLUGINS_DIR=/app/plugins

# Frontend
VITE_API_BASE_URL=/api
EOF

# Secure environment file
chmod 600 .env
```

### 3. Deploy with Docker Compose

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    restart: unless-stopped
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - SECRET_KEY=${SECRET_KEY}
      - DEBUG=${DEBUG}
      - LOG_LEVEL=${LOG_LEVEL}
      - LOG_FORMAT=${LOG_FORMAT}
      - PYTHONUNBUFFERED=1
      - CODEX_PLUGINS_DIR=/app/plugins
    volumes:
      - ./data:/app/data:rw
      - ./plugins:/app/plugins:ro
    command: >
      sh -c "alembic upgrade head && 
             python -m codex.main"
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        - VITE_API_BASE_URL=${VITE_API_BASE_URL}
    restart: unless-stopped
    volumes:
      - ./plugins:/plugins:ro
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:80"]
      interval: 30s
      timeout: 10s
      retries: 3
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
      - ./logs/nginx:/var/log/nginx:rw
    depends_on:
      - backend
      - frontend
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:80/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

Deploy:
```bash
docker compose -f docker-compose.prod.yml up -d
```

### 4. Configure Nginx

Create `nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream backend {
        server backend:8000;
    }

    upstream frontend {
        server frontend:80;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=login_limit:10m rate=5r/m;

    server {
        listen 80;
        server_name _;

        # Security headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "no-referrer-when-downgrade" always;

        # Logging
        access_log /var/log/nginx/access.log;
        error_log /var/log/nginx/error.log;

        # Frontend
        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # API endpoints
        location /api/ {
            limit_req zone=api_limit burst=20 nodelay;
            
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Request-ID $request_id;
            
            # CORS headers (adjust for production)
            add_header Access-Control-Allow-Origin $http_origin always;
            add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, PATCH, OPTIONS" always;
            add_header Access-Control-Allow-Headers "Authorization, Content-Type" always;
            add_header Access-Control-Allow-Credentials "true" always;
        }

        # WebSocket endpoint
        location /api/v1/ws/ {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_connect_timeout 7d;
            proxy_send_timeout 7d;
            proxy_read_timeout 7d;
        }

        # Login rate limiting
        location /api/v1/users/token {
            limit_req zone=login_limit burst=3 nodelay;
            
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        # Health check
        location /health {
            access_log off;
            proxy_pass http://backend/health;
        }
    }
}
```

### 5. SSL/TLS Setup with Let's Encrypt

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d codex.example.com

# Auto-renewal is configured via systemd timer
sudo systemctl status certbot.timer
```

Update `nginx.conf` to use SSL:

```nginx
server {
    listen 80;
    server_name codex.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name codex.example.com;

    ssl_certificate /etc/letsencrypt/live/codex.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/codex.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # ... rest of configuration
}
```

### 6. Create Admin User

```bash
docker compose exec backend python << EOF
from codex.db.database import get_system_session_sync
from codex.db.models.system import User
from codex.api.auth import get_password_hash

session = get_system_session_sync()
admin = User(
    username="admin",
    email="admin@example.com",
    hashed_password=get_password_hash("CHANGE_ME"),
    is_superuser=True
)
session.add(admin)
session.commit()
print(f"Admin user created: {admin.username}")
EOF
```

### 7. Verify Deployment

```bash
# Check service health
docker compose ps
docker compose logs backend
docker compose logs frontend

# Test API
curl https://codex.example.com/health

# Test frontend
curl -I https://codex.example.com/
```

## Cloud Deployments

### AWS Deployment

**Services Used:**
- EC2: Application server
- RDS: PostgreSQL database (optional)
- S3: Backup storage
- CloudFront: CDN (optional)
- Route 53: DNS

**Steps:**

1. **Launch EC2 Instance:**
   ```bash
   # Choose Ubuntu 22.04 LTS
   # Instance type: t3.medium or larger
   # Security group: Allow 80, 443, 22
   ```

2. **Connect and Deploy:**
   ```bash
   ssh ubuntu@<ec2-ip>
   # Follow "Production Deployment" steps above
   ```

3. **Configure RDS (Optional):**
   ```bash
   # Create PostgreSQL RDS instance
   # Update .env:
   DATABASE_URL=postgresql://user:pass@codex-db.xxxxx.rds.amazonaws.com:5432/codex
   ```

4. **Setup S3 Backups:**
   ```bash
   # Install AWS CLI
   sudo apt install awscli
   
   # Configure credentials
   aws configure
   
   # Backup script
   cat > /opt/codex/backup.sh << 'EOF'
   #!/bin/bash
   BACKUP_DIR=/opt/codex/backups
   DATE=$(date +%Y%m%d-%H%M%S)
   
   # Backup databases
   docker compose exec -T backend \
     sqlite3 /app/data/codex_system.db ".backup /tmp/system-$DATE.db"
   
   # Sync to S3
   aws s3 sync $BACKUP_DIR s3://codex-backups/
   EOF
   
   chmod +x /opt/codex/backup.sh
   
   # Add to crontab
   echo "0 2 * * * /opt/codex/backup.sh" | crontab -
   ```

### DigitalOcean Deployment

**Droplet Setup:**

```bash
# Create droplet via web UI or CLI
doctl compute droplet create codex \
  --image ubuntu-22-04-x64 \
  --size s-2vcpu-4gb \
  --region nyc3

# Get IP
doctl compute droplet list

# SSH and deploy
ssh root@<droplet-ip>
# Follow "Production Deployment" steps
```

**Managed Database:**
```bash
# Create managed PostgreSQL cluster
doctl databases create codex-db \
  --engine pg \
  --region nyc3 \
  --size db-s-1vcpu-2gb

# Get connection string
doctl databases connection codex-db

# Update .env with connection string
```

### Google Cloud Platform

**Compute Engine:**

```bash
# Create VM
gcloud compute instances create codex \
  --machine-type=e2-medium \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=50GB

# Configure firewall
gcloud compute firewall-rules create allow-http-https \
  --allow=tcp:80,tcp:443

# SSH and deploy
gcloud compute ssh codex
# Follow "Production Deployment" steps
```

**Cloud SQL (Optional):**
```bash
# Create PostgreSQL instance
gcloud sql instances create codex-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1

# Get connection name
gcloud sql instances describe codex-db | grep connectionName
```

### Azure Deployment

**Virtual Machine:**

```bash
# Create resource group
az group create --name codex-rg --location eastus

# Create VM
az vm create \
  --resource-group codex-rg \
  --name codex-vm \
  --image UbuntuLTS \
  --size Standard_B2s \
  --admin-username azureuser \
  --generate-ssh-keys

# Open ports
az vm open-port --port 80 --resource-group codex-rg --name codex-vm
az vm open-port --port 443 --resource-group codex-rg --name codex-vm

# SSH and deploy
ssh azureuser@<vm-ip>
# Follow "Production Deployment" steps
```

## Kubernetes Deployment

### Prerequisites

- Kubernetes cluster (1.24+)
- kubectl configured
- Helm 3 (optional)

### 1. Create Namespace

```bash
kubectl create namespace codex
kubectl config set-context --current --namespace=codex
```

### 2. Create Secrets

```bash
# Generate secret key
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# Create secret
kubectl create secret generic codex-secrets \
  --from-literal=secret-key=$SECRET_KEY \
  --from-literal=database-url=postgresql://user:pass@postgres:5432/codex
```

### 3. Deploy PostgreSQL

```yaml
# postgres.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15-alpine
        env:
        - name: POSTGRES_DB
          value: codex
        - name: POSTGRES_USER
          value: codex
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: codex-secrets
              key: postgres-password
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
      volumes:
      - name: postgres-storage
        persistentVolumeClaim:
          claimName: postgres-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
```

### 4. Deploy Backend

```yaml
# backend.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: codex-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: codex-backend
  template:
    metadata:
      labels:
        app: codex-backend
    spec:
      containers:
      - name: backend
        image: codex-backend:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 8000
        env:
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: codex-secrets
              key: secret-key
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: codex-secrets
              key: database-url
        - name: DEBUG
          value: "false"
        - name: LOG_LEVEL
          value: "INFO"
        - name: LOG_FORMAT
          value: "json"
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
        volumeMounts:
        - name: data
          mountPath: /app/data
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: codex-data-pvc
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: codex-data-pvc
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 50Gi
---
apiVersion: v1
kind: Service
metadata:
  name: codex-backend-service
spec:
  selector:
    app: codex-backend
  ports:
  - protocol: TCP
    port: 8000
    targetPort: 8000
  type: ClusterIP
```

### 5. Deploy Frontend

```yaml
# frontend.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: codex-frontend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: codex-frontend
  template:
    metadata:
      labels:
        app: codex-frontend
    spec:
      containers:
      - name: frontend
        image: codex-frontend:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 80
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: codex-frontend-service
spec:
  selector:
    app: codex-frontend
  ports:
  - protocol: TCP
    port: 80
    targetPort: 80
  type: ClusterIP
```

### 6. Configure Ingress

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: codex-ingress
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/proxy-body-size: "100m"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - codex.example.com
    secretName: codex-tls
  rules:
  - host: codex.example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: codex-backend-service
            port:
              number: 8000
      - path: /
        pathType: Prefix
        backend:
          service:
            name: codex-frontend-service
            port:
              number: 80
```

### 7. Deploy

```bash
kubectl apply -f postgres.yaml
kubectl apply -f backend.yaml
kubectl apply -f frontend.yaml
kubectl apply -f ingress.yaml

# Wait for pods
kubectl get pods -w

# Check services
kubectl get services
kubectl get ingress
```

### 8. Scale

```bash
# Scale backend
kubectl scale deployment codex-backend --replicas=5

# Auto-scale
kubectl autoscale deployment codex-backend \
  --cpu-percent=70 \
  --min=2 \
  --max=10
```

## Security Configuration

### Environment Variables

**Required:**
- `SECRET_KEY`: 64-character hex string (CRITICAL - never use default)
- `DATABASE_URL`: Database connection string

**Optional Security:**
- `ALLOWED_HOSTS`: Comma-separated list of allowed hostnames
- `CORS_ORIGINS`: Comma-separated list of allowed CORS origins
- `SESSION_TIMEOUT`: JWT expiration in minutes (default: 30)

**Generate Secure SECRET_KEY:**
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### Firewall Configuration

```bash
# UFW (Ubuntu)
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Check status
sudo ufw status verbose
```

### Docker Security

```bash
# Run as non-root user
# Add to Dockerfile:
USER codex:codex

# Read-only filesystem where possible
# In docker-compose.yml:
volumes:
  - ./plugins:/app/plugins:ro

# Limit resources
# In docker-compose.yml:
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 4G
```

### Database Security

**PostgreSQL:**
```sql
-- Create dedicated user
CREATE USER codex WITH PASSWORD 'strong_password';
CREATE DATABASE codex OWNER codex;
GRANT ALL PRIVILEGES ON DATABASE codex TO codex;

-- Revoke public access
REVOKE ALL ON DATABASE codex FROM PUBLIC;
```

**SQLite:**
```bash
# Restrict file permissions
chmod 600 /app/data/codex_system.db
chown codex:codex /app/data/codex_system.db
```

## Monitoring & Maintenance

### Health Checks

```bash
# API health
curl https://codex.example.com/health

# Docker health
docker compose ps
```

### Log Management

```bash
# View logs
docker compose logs -f backend
docker compose logs -f frontend

# Log rotation (configure in docker-compose.yml)
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### Database Maintenance

```bash
# SQLite vacuum (monthly)
docker compose exec backend \
  sqlite3 /app/data/codex_system.db "VACUUM; ANALYZE;"

# Check integrity
docker compose exec backend \
  sqlite3 /app/data/codex_system.db "PRAGMA integrity_check;"
```

### Update Procedure

```bash
# Pull latest code
cd /opt/codex
git pull

# Rebuild containers
docker compose -f docker-compose.prod.yml build

# Apply migrations
docker compose -f docker-compose.prod.yml exec backend \
  alembic upgrade head

# Restart services (zero-downtime with health checks)
docker compose -f docker-compose.prod.yml up -d

# Verify
docker compose ps
curl https://codex.example.com/health
```

## Troubleshooting

### Common Issues

**Backend won't start:**
```bash
# Check logs
docker compose logs backend

# Common fixes:
# 1. SECRET_KEY not set
# 2. Database migrations not applied
# 3. Permissions issues

# Apply migrations
docker compose exec backend alembic upgrade head
```

**Frontend can't reach backend:**
```bash
# Check network
docker compose exec frontend ping backend

# Check environment
docker compose exec frontend env | grep VITE_API_BASE_URL

# Rebuild with correct API URL
docker compose build frontend
docker compose up -d frontend
```

**Database locked errors:**
```bash
# SQLite busy - check for zombie processes
docker compose exec backend ps aux | grep python

# Restart backend
docker compose restart backend
```

**WebSocket connection fails:**
```bash
# Check nginx config for WebSocket proxy
# Ensure these headers are set:
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
```

### Debug Mode

```bash
# Enable debug mode
echo "DEBUG=true" >> .env
docker compose restart backend

# View detailed logs
docker compose logs -f backend

# Disable after debugging
sed -i 's/DEBUG=true/DEBUG=false/' .env
docker compose restart backend
```

## Backup & Recovery

### Automated Backups

```bash
# Create backup script
cat > /opt/codex/scripts/backup.sh << 'EOF'
#!/bin/bash
set -e

BACKUP_DIR="/opt/codex/backups"
DATE=$(date +%Y%m%d-%H%M%S)
KEEP_DAYS=30

mkdir -p $BACKUP_DIR

# Backup system database
docker compose exec -T backend \
  sqlite3 /app/data/codex_system.db ".backup /tmp/system-$DATE.db"
docker compose cp backend:/tmp/system-$DATE.db $BACKUP_DIR/

# Backup notebooks (tar)
docker compose exec -T backend \
  tar czf /tmp/notebooks-$DATE.tar.gz /app/data/workspaces
docker compose cp backend:/tmp/notebooks-$DATE.tar.gz $BACKUP_DIR/

# Cleanup old backups
find $BACKUP_DIR -type f -mtime +$KEEP_DAYS -delete

# Optional: Upload to S3/GCS
# aws s3 sync $BACKUP_DIR s3://codex-backups/

echo "Backup completed: $DATE"
EOF

chmod +x /opt/codex/scripts/backup.sh

# Schedule daily backups (2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/codex/scripts/backup.sh") | crontab -
```

### Manual Backup

```bash
# Stop services
docker compose down

# Backup data directory
tar czf codex-backup-$(date +%Y%m%d).tar.gz data/

# Restart services
docker compose up -d
```

### Restore from Backup

```bash
# Stop services
docker compose down

# Restore data
tar xzf codex-backup-20240101.tar.gz

# Verify database integrity
sqlite3 data/codex_system.db "PRAGMA integrity_check;"

# Start services
docker compose up -d

# Verify functionality
curl https://codex.example.com/health
```

### Disaster Recovery

**RTO (Recovery Time Objective):** < 1 hour
**RPO (Recovery Point Objective):** < 24 hours

**Recovery Steps:**

1. **Provision New Server:**
   ```bash
   # Launch new VM/instance
   # Install Docker
   # Clone repository
   ```

2. **Restore Data:**
   ```bash
   # Download latest backup
   # Extract to data directory
   ```

3. **Deploy Application:**
   ```bash
   # Configure .env
   # Start services
   docker compose -f docker-compose.prod.yml up -d
   ```

4. **Verify:**
   ```bash
   # Check services
   docker compose ps
   
   # Test login
   curl -X POST https://codex.example.com/api/v1/users/token \
     -d "username=admin&password=password"
   
   # Verify data
   # Login and check workspaces/notebooks
   ```

5. **Update DNS:**
   ```bash
   # Point domain to new server IP
   # Wait for propagation
   ```

---

*For questions or issues, please consult the [ARCHITECTURE.md](ARCHITECTURE.md) documentation or open an issue in the repository.*
