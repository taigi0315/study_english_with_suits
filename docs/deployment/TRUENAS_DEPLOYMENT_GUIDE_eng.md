# TrueNAS SCALE Deployment Guide (English)

## Overview

This guide explains how to deploy the LangFlix application on **TrueNAS SCALE** (the Linux-based community edition of TrueNAS). TrueNAS SCALE ships with Kubernetes and Docker tooling, so LangFlix can run directly on the system without creating additional virtual machines. We provide two supported approaches:

1. **Docker Compose CLI (recommended for CLI workflows):** Manage the stack from the SCALE shell.
2. **Apps → Docker Compose App (GUI workflow):** Import the `docker-compose.truenas.yml` file through the Apps catalog.

Choose the method that matches your operational style. Both approaches rely on TrueNAS datasets to store media, application output, logs, and backups. The examples below assume the LangFlix project lives at `/mnt/Pool_2/Projects/langflix`, matching the prompt:

```bash
truenas_admin@truenas[/mnt/Pool_2/Projects/langflix]$ pwd
/mnt/Pool_2/Projects/langflix
```

Adjust paths if your datasets differ.

---

## Prerequisites

### Platform
- TrueNAS SCALE 23.10 (Cobia) or newer
- Admin access to the TrueNAS SCALE web UI
- Apps service enabled (k3s + Docker)

### Storage
- Existing dataset containing media library (read-only inside the container)
- New dataset for LangFlix application data (read/write)
- Optional datasets for logs and backups, or use subdirectories of the application dataset

### Credentials and API keys
- PostgreSQL password
- Redis password
- Gemini API key (and any optional external API credentials)

### Networking
- Static IP or DHCP reservation for the TrueNAS SCALE host
- Open LAN firewall ports for API access (`8000` by default)
- Reverse proxy (optional) if exposing externally

---

## Step 1: Prepare Datasets on TrueNAS SCALE

1. **Create/confirm datasets**
   - Web UI → **Storage** → **Pools**
   - For example:
     - `mnt/Pool_2/Media` (existing media files, read-only)
     - `mnt/Pool_2/Projects/langflix` (LangFlix application data and repository)
2. **Set permissions**
   - Keep default owner (`root:root`); we will mount with UID/GID 1000 inside containers using bind mounts and adjust permissions later.
3. **Record absolute paths** for use in the `.env` file and Docker Compose volumes.

---

## Step 2: Access the SCALE Shell

You can use either of the following:
- Web UI → **System Settings** → **Shell**
- SSH into SCALE: `ssh root@truenas-ip`

> **Tip:** Use `sudo -iu apps` if you prefer to run Docker commands as the built-in `apps` user (introduced in Cobia). For simplicity, the guide uses `root`. Adjust according to your security policies.

---

## Step 3: Install Docker Compose CLI (if needed)

TrueNAS SCALE bundles Docker and the Compose plugin, but confirm availability:

```bash
docker version
docker compose version
```

If the Compose plugin is missing, reinstall it:

```bash
apt update
apt install -y docker-compose-plugin
```

SCALE package management is supported but avoid dist-upgrade operations—stick to targeted installs.

---

## Step 4: Clone LangFlix Repository

Choose a location within your application dataset (here `/mnt/Pool_2/Projects/langflix`):

```bash
cd /mnt/Pool_2/Projects
git clone https://github.com/your-username/study_english_with_sutis.git langflix
cd langflix
```

You can fork or pin a specific revision as needed.

---

## Step 5: Create Supporting Directories

```bash
mkdir -p /mnt/Pool_2/Projects/langflix/{output,logs,cache,assets,db-backups}
chown -R 1000:1000 /mnt/Pool_2/Projects/langflix
chmod -R 755 /mnt/Pool_2/Projects/langflix
```

The UID/GID `1000:1000` matches the default unprivileged user inside many containers. Adjust if your images use a different UID.

---

## Step 6: Configure Environment Variables

Create the `.env` file under `deploy/`:

```bash
cd /mnt/Pool_2/Projects/langflix/deploy
cat <<'EOF' > .env
# TrueNAS SCALE dataset paths
TRUENAS_MEDIA_PATH=/mnt/Pool_2/Media  # Adjust to your actual media dataset root
TRUENAS_DATA_PATH=/mnt/Pool_2/Projects/langflix

# Database configuration
POSTGRES_USER=langflix
POSTGRES_PASSWORD=change_me_securely
POSTGRES_DB=langflix

# Redis configuration
REDIS_PASSWORD=change_me_securely
LANGFLIX_REDIS_URL=redis://:${REDIS_PASSWORD}@langflix-redis:6379/0

# UI configuration
LANGFLIX_UI_PORT=5000
LANGFLIX_OUTPUT_DIR=/data/output
LANGFLIX_MEDIA_DIR=/media/shows
LANGFLIX_API_BASE_URL=http://langflix-api:8000

# Backend server configuration
UVICORN_HOST=0.0.0.0
UVICORN_PORT=8000
UVICORN_RELOAD=false

# API keys
GEMINI_API_KEY=your_gemini_api_key_here
GOOGLE_API_KEY_1=
LEMONFOX_API_KEY=

# Network configuration
API_PORT=8000
POSTGRES_PORT=5432
REDIS_PORT=6379

# Logging
LOG_LEVEL=INFO
EOF
```

Update passwords and keys before production use. Keep `.env` out of version control.

> **Tip:** If your media lives at a different location (e.g. `/mnt/Media/Shows`), set `TRUENAS_MEDIA_PATH` to the parent (`/mnt/Media`) and update the compose mount path if the folder name differs in case or structure. You can also replace the volume mapping with the exact path, e.g. `- /mnt/Media/Shows:/media/shows:ro`.

### YouTube OAuth Credentials

1. Download OAuth credentials from Google Cloud Console as `youtube_credentials.json`.
2. Create an empty `youtube_token.json` (the app will populate it after authentication).
3. Copy both files to `${TRUENAS_DATA_PATH}/assets/` on TrueNAS:
   ```bash
   scp youtube_credentials.json youtube_token.json \
       truenas_admin@truenas-ip:/mnt/Pool_2/Projects/langflix/assets/
   ```
4. Ensure proper ownership and permissions for the Docker user (UID/GID 1000):
   ```bash
   sudo chown 1000:1000 /mnt/Pool_2/Projects/langflix/assets/youtube_token.json
   sudo chmod 600 /mnt/Pool_2/Projects/langflix/assets/youtube_token.json
   sudo chmod 640 /mnt/Pool_2/Projects/langflix/assets/youtube_credentials.json
   ```
5. The compose file mounts these files into the UI container automatically (read-only for credentials, writable for token).
---

## Step 7: Review Docker Compose File

Open `deploy/docker-compose.truenas.yml` and confirm volumes use dataset paths:

```yaml
services:
  api:
    volumes:
      - ${TRUENAS_MEDIA_PATH}:/media/shows:ro
      - ${TRUENAS_DATA_PATH}/output:/data/output:rw
      - ${TRUENAS_DATA_PATH}/logs:/var/log/langflix:rw
      - ${TRUENAS_DATA_PATH}/cache:/data/cache:rw
  langflix-ui:
    environment:
      - LANGFLIX_API_BASE_URL=http://langflix-api:8000
      - LANGFLIX_OUTPUT_DIR=/data/output
      - LANGFLIX_MEDIA_DIR=/media/shows
    ports:
      - "${UI_PORT:-5000}:5000"
    volumes:
      - ${TRUENAS_MEDIA_PATH}:/media/shows:ro
      - ${TRUENAS_DATA_PATH}/output:/data/output:rw
      - ${TRUENAS_DATA_PATH}/assets:/data/assets:ro
      - ${TRUENAS_DATA_PATH}/logs:/data/logs:rw
      - ${TRUENAS_DATA_PATH}/cache:/app/cache:rw
      - ${TRUENAS_DATA_PATH}/assets/youtube_credentials.json:/app/youtube_credentials.json:ro
      - ${TRUENAS_DATA_PATH}/assets/youtube_token.json:/app/youtube_token.json:rw
```

Adjust mount paths if your dataset layout differs.

---

## Step 8A: Deploy via Docker Compose CLI (Shell Workflow)

```bash
cd /mnt/Pool_2/Projects/langflix/deploy

# Pull or build images
docker compose -f docker-compose.truenas.yml pull
# or
docker compose -f docker-compose.truenas.yml build

# Start stack
docker compose -f docker-compose.truenas.yml up -d

# Verify
docker compose -f docker-compose.truenas.yml ps
```

If you need to run commands as the `apps` user:

```bash
sudo -iu apps
cd /mnt/Pool_2/Projects/langflix/deploy
docker compose -f docker-compose.truenas.yml up -d
```

---

## Step 8B: Deploy via Apps → Docker Compose App (GUI Workflow)

1. Web UI → **Apps** → **Launch Docker Compose App** (Cobia and later).
2. Set **Application Name:** `langflix`.
3. Paste the contents of `docker-compose.truenas.yml`.
4. Enable **Use Custom Environment File** and paste `.env` contents or define key/value pairs manually.
5. Confirm storage paths in the **Volumes** section.
6. Click **Install**. SCALE will create a Compose app under the `ix-applications` dataset.

> The GUI workflow is useful when you prefer declarative management and visibility in the Apps dashboard.

---

## Step 9: Verify Services

```bash
curl http://truenas-ip:8000/health
curl http://truenas-ip:8000/docs
curl http://truenas-ip:5000/
```

Check logs:

```bash
docker compose -f docker-compose.truenas.yml logs -f api
docker compose -f docker-compose.truenas.yml logs -f langflix-ui
docker compose -f docker-compose.truenas.yml logs -f postgres
```

Inspect container mounts:

```bash
docker exec -it langflix-api ls -lah /media/shows
docker exec -it langflix-api ls -lah /data/output
docker exec -it langflix-ui ls -lah /data/output
```

---

## Step 10: Networking & Security

- Ensure the SCALE firewall or upstream router allows inbound traffic to ports `8000` (API) and `5000` (UI).
- For public exposure, place LangFlix behind a reverse proxy (Traefik, Nginx Proxy Manager, Caddy, etc.).
- Keep `.env` files and secrets restricted to privileged users.
- Regenerate PostgreSQL/Redis passwords periodically.

---

## Step 11: Maintenance

### Updating LangFlix

```bash
cd /mnt/Pool_2/Projects/langflix
git pull
cd deploy
docker compose -f docker-compose.truenas.yml pull
docker compose -f docker-compose.truenas.yml up -d
```

### Development Cycle / Resetting Environment

Before rebuilding or applying configuration changes, stop and clean existing containers/resources:

```bash
cd /mnt/Pool_2/Projects/langflix/deploy

# Stop containers (preserves volumes)
sudo docker compose -f docker-compose.truenas.yml down

# Optional: remove volumes (Redis data, etc.)
sudo docker compose -f docker-compose.truenas.yml down -v

# Optional: remove built images to force rebuild
sudo docker compose -f docker-compose.truenas.yml down --rmi local
sudo docker system prune -f
```

### Backups

```bash
docker exec langflix-postgres pg_dump -U langflix langflix \
  > /mnt/Pool_2/Projects/langflix/db-backups/backup_$(date +%Y%m%d_%H%M%S).sql
```

Leverage TrueNAS replication and snapshot tasks for dataset-level backups.

### Monitoring

```bash
docker compose -f docker-compose.truenas.yml logs -f
docker stats
```

Consider integrating SCALE metrics with Prometheus/Grafana for long-term observability.

---

## Troubleshooting

### Containers will not start
- Inspect Compose logs: `docker compose -f docker-compose.truenas.yml logs`
- Confirm dataset paths exist and are mounted
- Check file permissions (`ls -lah /mnt/Pool_2/Projects/langflix`)
- If only the UI container fails, verify `${TRUENAS_DATA_PATH}/assets` exists and that `LANGFLIX_API_BASE_URL` resolves to `langflix-api`.

### PostgreSQL/Redis connection issues
- Verify `.env` credentials
- Test directly in containers:
  ```bash
  docker exec langflix-postgres pg_isready -U langflix
  docker exec langflix-redis redis-cli -a "$REDIS_PASSWORD" ping
  ```

### Media path not accessible
- Confirm dataset path in `.env` → `TRUENAS_MEDIA_PATH`
- Ensure the dataset is exported correctly and accessible to the container user
- Check container mount: `docker exec langflix-api ls /media`

### UI logs show PostgreSQL connection refused
- This happens when `DATABASE_ENABLED=false` (default) and the PostgreSQL service is not running.
- If you need database-backed features (quota tracking, scheduler, etc.), set `DATABASE_ENABLED=true` in `.env` and start the database profile:
  ```bash
  sudo docker compose -f docker-compose.truenas.yml --profile database up -d
  ```
- Otherwise, the warnings can be ignored.
### Resource constraints
- Increase dataset quotas or host RAM/CPU
- Use Compose `deploy.resources` limits to prevent resource starvation

---

## Summary

1. Prepare datasets for media and application data.
2. Clone LangFlix, configure `.env`, and verify Compose volumes.
3. Deploy using the Docker Compose CLI or Apps GUI.
4. Validate service health and secure access.
5. Maintain via Git updates, Docker image refresh, and dataset snapshots.

TrueNAS SCALE provides a robust platform for container workloads while retaining the power of ZFS for storage management.

**Access URLs:**
- API: `http://truenas-ip:8000`
- API Documentation: `http://truenas-ip:8000/docs`
- LangFlix UI Dashboard: `http://truenas-ip:5000`

---

## Additional Resources

- TrueNAS SCALE Documentation: <https://www.truenas.com/docs/scale/>
- Docker Compose App Documentation: <https://www.truenas.com/docs/scale/scaletutorials/dockercompose/>
- LangFlix Project Documentation: `docs/project.md`

---

**Last Updated:** 2025-11-10

