# TrueNAS Deployment Guide (English)

## Overview

This guide explains how to deploy the LangFlix application to a TrueNAS server.

**Current Situation:**
- Running PostgreSQL, Redis, and application in Docker on macOS
- Media files stored on TrueNAS server
- Need to run all services on TrueNAS and access media files

**Deployment Targets:**
- TrueNAS Scale (Linux-based, Docker support) - **Recommended**
- TrueNAS Core (FreeBSD-based) - Requires VM or Docker Desktop

---

## Prerequisites

### 1. Check TrueNAS Version

**TrueNAS Scale (Recommended):**
- Linux-based with direct Docker support
- Can use Docker Compose
- Easiest deployment method

**TrueNAS Core:**
- FreeBSD-based, no direct Docker support
- Need to run Docker Desktop in VM or
- Create separate Linux VM

### 2. Requirements

- SSH access to TrueNAS server
- Docker and Docker Compose installed (Apps in TrueNAS Scale)
- Knowledge of TrueNAS media file paths
- GitHub repository access or ability to upload project files

---

## Step 1: Prepare TrueNAS Environment

### Docker Setup on TrueNAS Scale

1. **Access TrueNAS Web UI**
   - Open browser and navigate to TrueNAS IP (e.g., `http://192.168.1.100`)

2. **Install Apps (Docker included)**
   - Click **Apps** in left menu
   - Search for **Docker** or **Docker Compose** in **Available Applications**
   - Install (TrueNAS Scale uses Kubernetes, so Apps automatically provides Docker)

3. **Shell Access**
   - Click **System Settings** → **Shell** in left menu
   - Or SSH: `ssh admin@truenas-ip`

### Check TrueNAS Paths

Check media file paths on TrueNAS:

```bash
# Run on TrueNAS shell
ls -la /mnt/

# Common patterns:
# /mnt/pool/media/shows
# /mnt/tank/media/shows
# /mnt/storage/media/shows
```

**Important:** Note this path for use in docker-compose.yml later.

---

## Step 2: Prepare Project Files

### Option A: Clone from Git (Recommended)

```bash
# Run on TrueNAS shell
cd /mnt/pool/apps/  # Or your desired path
git clone https://github.com/your-username/study_english_with_sutis.git langflix
cd langflix
```

### Option B: Upload Files Directly

1. Upload files via SMB/NFS share
2. Or use `scp`:
   ```bash
   # Run on local Mac
   scp -r /path/to/project admin@truenas-ip:/mnt/pool/apps/langflix
   ```

---

## Step 3: Configure Environment Variables

Create `.env` file in `deploy/` directory:

```bash
cd /mnt/pool/apps/langflix/deploy
nano .env
```

Enter the following:

```bash
# TrueNAS Path Settings (change to actual paths)
# Path where media files are stored
TRUENAS_MEDIA_PATH=/mnt/pool/media

# Application data storage path
TRUENAS_DATA_PATH=/mnt/pool/apps/langflix

# Database Password
POSTGRES_PASSWORD=your_secure_password_here

# Redis Password
REDIS_PASSWORD=your_redis_password_here

# API Keys (Required)
GEMINI_API_KEY=your_gemini_api_key_here

# Optional API Keys
GOOGLE_API_KEY_1=
LEMONFOX_API_KEY=

# Port Settings (Optional)
API_PORT=8000
POSTGRES_PORT=5432
REDIS_PORT=6379

# Log Level
LOG_LEVEL=INFO
```

**Important:**
- Change `TRUENAS_MEDIA_PATH` to actual TrueNAS media path
- `TRUENAS_DATA_PATH` is where application data will be stored
- Change passwords to secure ones

---

## Step 4: Create Directory Structure

Create necessary directories on TrueNAS:

```bash
# Create application data directories
sudo mkdir -p /mnt/pool/apps/langflix/{output,logs,cache,assets,db-backups}

# Set permissions (give write access to Docker user)
sudo chown -R 1000:1000 /mnt/pool/apps/langflix
sudo chmod -R 755 /mnt/pool/apps/langflix

# Verify media path (read-only access is sufficient)
ls -la /mnt/pool/media/shows
```

---

## Step 5: Verify Docker Compose File

The `deploy/docker-compose.truenas.yml` file is ready.

Verify key settings:

```yaml
volumes:
  # Media files (read-only)
  - ${TRUENAS_MEDIA_PATH}/shows:/media/shows:ro
  
  # Output directory (writable)
  - ${TRUENAS_DATA_PATH}/langflix/output:/data/output:rw
```

Verify that paths in `.env` file are correct.

---

## Step 6: Build and Run Docker Images

### Run on TrueNAS Scale

```bash
cd /mnt/pool/apps/langflix/deploy

# Start services with Docker Compose
docker-compose -f docker-compose.truenas.yml up -d

# Check logs
docker-compose -f docker-compose.truenas.yml logs -f

# Check service status
docker-compose -f docker-compose.truenas.yml ps
```

### Using Dockge

1. **Access Dockge Web UI**
   - Open browser to `http://truenas-ip:31014`

2. **Create New Stack**
   - Click "+ Compose"
   - Stack Name: `langflix`

3. **Copy docker-compose.truenas.yml content**
   - Paste file content into Dockge's YAML editor

4. **Set Environment Variables**
   - Enter environment variables in ".env" section

5. **Click Deploy**

---

## Step 7: Verify Services

### Check API Status

```bash
# API health check
curl http://localhost:8000/health

# Or in browser
http://truenas-ip:8000/health
```

### Check API Documentation

Open in browser:
```
http://truenas-ip:8000/docs
```

### Check Container Status

```bash
# All container status
docker ps

# Specific service logs
docker logs langflix-api
docker logs langflix-celery-worker
docker logs langflix-postgres
docker logs langflix-redis
```

### Verify Media File Access

```bash
# Check media files inside container
docker exec langflix-api ls -la /media/shows

# Check output directory
docker exec langflix-api ls -la /data/output
```

---

## Step 8: Network Access Configuration

### TrueNAS Firewall Settings

In TrueNAS Web UI:
1. **Network** → **Firewall** menu
2. Open required ports:
   - `8000` (API)
   - `5432` (PostgreSQL - internal network only)
   - `6379` (Redis - internal network only)

### External Access (Optional)

To access from outside:
1. Set up port forwarding on router
2. Or set up reverse proxy (Nginx, Traefik, etc.)

---

## Troubleshooting

### Containers Won't Start

**Check:**
```bash
# Check logs
docker-compose -f docker-compose.truenas.yml logs

# Specific service logs
docker logs langflix-api
```

**Common Issues:**

1. **Path doesn't exist**
   ```bash
   # Create directories
   sudo mkdir -p /mnt/pool/apps/langflix/{output,logs,cache}
   ```

2. **Permission issues**
   ```bash
   # Grant permissions to Docker user
   sudo chown -R 1000:1000 /mnt/pool/apps/langflix
   sudo chmod -R 755 /mnt/pool/apps/langflix
   ```

3. **Cannot access media path**
   ```bash
   # Check media path
   ls -la /mnt/pool/media/shows
   
   # Check from container
   docker exec langflix-api ls -la /media/shows
   ```

### Database Connection Failed

**Check:**
```bash
# PostgreSQL container status
docker ps | grep postgres

# PostgreSQL logs
docker logs langflix-postgres

# Test connection
docker exec langflix-postgres pg_isready -U langflix
```

### Redis Connection Failed

**Check:**
```bash
# Redis container status
docker ps | grep redis

# Redis logs
docker logs langflix-redis

# Test connection
docker exec langflix-redis redis-cli -a your_password ping
```

### Cannot Find Media Files

**Check:**
```bash
# Check media path on host
ls -la /mnt/pool/media/shows

# Check from container
docker exec langflix-api ls -la /media/shows

# Check environment variables
docker exec langflix-api env | grep LANGFLIX_STORAGE
```

**Solution:**
- Verify `TRUENAS_MEDIA_PATH` in `.env` file
- Check volume mount paths in `docker-compose.truenas.yml`
- Verify media path actually exists

---

## Updates and Maintenance

### Update Application

```bash
cd /mnt/pool/apps/langflix/deploy

# Get latest code from Git
cd ..
git pull
cd deploy

# Rebuild images and restart
docker-compose -f docker-compose.truenas.yml build
docker-compose -f docker-compose.truenas.yml up -d

# Or restart specific service only
docker-compose -f docker-compose.truenas.yml restart langflix-api
```

### Database Backup

```bash
# PostgreSQL backup
docker exec langflix-postgres pg_dump -U langflix langflix > /mnt/pool/apps/langflix/db-backups/backup_$(date +%Y%m%d_%H%M%S).sql

# Create automatic backup script (optional)
```

### Check Logs

```bash
# All service logs
docker-compose -f docker-compose.truenas.yml logs -f

# Specific service logs
docker-compose -f docker-compose.truenas.yml logs -f langflix-api

# Check log files (TrueNAS host)
tail -f /mnt/pool/apps/langflix/logs/langflix.log
```

---

## Resource Management

### Check Resource Usage

```bash
# Container resource usage
docker stats

# Disk usage
docker system df
```

### Adjust Resource Limits

Adjust resource limits in `docker-compose.truenas.yml` based on TrueNAS resources:

```yaml
deploy:
  resources:
    limits:
      cpus: '4'      # Number of CPU cores
      memory: 8G     # Memory limit
```

---

## Security Considerations

1. **Change Passwords**
   - Change default passwords in `.env` file to secure ones
   - Strengthen PostgreSQL and Redis passwords

2. **Network Isolation**
   - PostgreSQL and Redis should only be accessible from internal network
   - Only expose API to external

3. **File Permissions**
   - Mount media files as read-only (`:ro`)
   - Grant write permissions to output directory only to necessary users

4. **Regular Updates**
   - Regularly update Docker images
   - Apply security patches

---

## Summary

**Deployment Steps Summary:**

1. ✅ Prepare TrueNAS environment (Docker, verify paths)
2. ✅ Prepare project files (Git clone or upload)
3. ✅ Configure environment variables (create `.env` file)
4. ✅ Create directory structure
5. ✅ Run Docker Compose
6. ✅ Verify services and test

**Key Paths:**
- Media files: `/mnt/pool/media/shows` (read-only)
- Application data: `/mnt/pool/apps/langflix/` (writable)
- Logs: `/mnt/pool/apps/langflix/logs/`
- Output: `/mnt/pool/apps/langflix/output/`

**Access URLs:**
- API: `http://truenas-ip:8000`
- API Documentation: `http://truenas-ip:8000/docs`
- Health Check: `http://truenas-ip:8000/health`

---

## Additional Resources

- [Dockge Setup Guide](DOCKGE_SETUP_eng.md)
- [Docker Network Media Path Configuration](DOCKER_NETWORK_MEDIA_eng.md)
- [CI/CD SSH Setup](CI_CD_SSH_SETUP.md)
- [API Reference](../API_REFERENCE.md)

---

**Last Updated:** 2025-01-30

