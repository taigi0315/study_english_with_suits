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

## Step 5: Create Supporting Directories and Set Permissions

Create the directories that Docker Compose will mount as volumes and **set proper permissions**. Skipping this step will cause containers to fail to start or result in file access errors.

### 5-1. Create Directories

```bash
cd /mnt/Pool_2/Projects/langflix

# Create required directories
sudo mkdir -p output logs cache assets db-backups
```

### 5-2. Set Directory Permissions (Critical!)

The user inside Docker containers uses UID/GID `1000:1000`. You must set permissions so this user can access files and directories on the host.

```bash
# Set permissions for Docker container user (UID/GID 1000)
sudo chown -R 1000:1000 output logs cache assets db-backups
sudo chmod -R 755 output logs cache assets db-backups
```

**Verify permissions:**
```bash
ls -la /mnt/Pool_2/Projects/langflix/
# Expected output:
# drwxr-xr-x 1 1000 1000 output
# drwxr-xr-x 1 1000 1000 logs
# drwxr-xr-x 1 1000 1000 cache
# drwxr-xr-x 1 1000 1000 assets
# drwxr-xr-x 1 1000 1000 db-backups
```

### 5-3. Resolve TrueNAS ACL Issues

Due to TrueNAS ACLs (Access Control Lists), `chmod`/`chown` may not work as expected. Try the following methods:

**Method 1: Use TrueNAS Web UI (Recommended)**
1. Web UI → **Storage** → **Pools**
2. Select dataset (e.g., `Pool_2/Projects/langflix`)
3. Click **Permissions**
4. For each directory (`output`, `logs`, `cache`, `assets`, `db-backups`):
   - **User**: Select `1000` or `apps`
   - **Group**: Select `1000`
   - **Mode**: Set `755`
   - Click **Apply**

**Method 2: Use midclt Command**
```bash
# Set permissions via TrueNAS API
sudo midclt call filesystem.setperm path=/mnt/Pool_2/Projects/langflix/output mode=755 user=1000 group=1000
sudo midclt call filesystem.setperm path=/mnt/Pool_2/Projects/langflix/logs mode=755 user=1000 group=1000
sudo midclt call filesystem.setperm path=/mnt/Pool_2/Projects/langflix/cache mode=755 user=1000 group=1000
sudo midclt call filesystem.setperm path=/mnt/Pool_2/Projects/langflix/assets mode=755 user=1000 group=1000
sudo midclt call filesystem.setperm path=/mnt/Pool_2/Projects/langflix/db-backups mode=755 user=1000 group=1000
```

> **Note:** If `midclt` command doesn't work, use TrueNAS web UI or contact your system administrator.

### 5-4. Set Media Path Permissions

The media file path must also be readable by containers:

```bash
# Verify media path (e.g., /mnt/Pool_2/Media/Shows/Suits)
MEDIA_PATH="/mnt/Pool_2/Media/Shows/Suits"  # Change to your actual path

# Set read permissions (containers only need read access)
sudo chown -R 1000:1000 "$MEDIA_PATH"
sudo chmod -R 755 "$MEDIA_PATH"

# Verify permissions
ls -la "$MEDIA_PATH" | head -5
```

**Test access from inside container:**
```bash
# Test after starting containers
sudo docker exec langflix-api ls -lah /media/shows
# If you get Permission denied error, recheck media path permissions
```

### 5-5. Set YouTube Credential File Permissions

If you plan to use YouTube features, credential file permissions must also be set correctly:

```bash
# Verify files exist
ls -la assets/youtube_credentials.json assets/youtube_token.json

# Set file permissions
sudo chown 1000:1000 assets/youtube_credentials.json
sudo chown 1000:1000 assets/youtube_token.json

# youtube_credentials.json: read-only (644)
sudo chmod 644 assets/youtube_credentials.json

# youtube_token.json: read/write (600, more secure)
sudo chmod 600 assets/youtube_token.json

# Verify permissions
ls -la assets/youtube_*.json
# Expected output:
# -rw-r--r-- 1 1000 1000 youtube_credentials.json
# -rw------- 1 1000 1000 youtube_token.json
```

**Test file access from inside container:**
```bash
# Test after starting containers
sudo docker exec langflix-ui cat /app/youtube_credentials.json | head -5
# If you get Permission denied error, recheck file permissions
```

> **Important:** UID/GID `1000:1000` matches the default unprivileged user inside many containers. Adjust if your images use a different UID.

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

> **Note:** The `.env` file is not mounted into Docker containers. All environment variables are passed directly via the `environment` section in Docker Compose, avoiding TrueNAS ACL permission issues. The `.env` file is only used by Docker Compose to read variables and pass them to the `environment` section.

> **Tip:** If your media lives at a different location (e.g. `/mnt/Media/Shows`), set `TRUENAS_MEDIA_PATH` to the parent (`/mnt/Media`) and update the compose mount path if the folder name differs in case or structure. You can also replace the volume mapping with the exact path, e.g. `- /mnt/Media/Shows:/media/shows:ro`.

### YouTube OAuth Credentials

1. Download OAuth credentials from Google Cloud Console as `youtube_credentials.json`.
   - See [YouTube Setup Guide](../youtube/YOUTUBE_SETUP_GUIDE_eng.md) for detailed setup instructions.

2. Create an empty `youtube_token.json` (the app will populate it after authentication).
   ```bash
   touch youtube_token.json
   ```

3. Copy both files to `${TRUENAS_DATA_PATH}/assets/` on TrueNAS.
   
   **From local computer:**
   ```bash
   # Using SMB mount (macOS)
   mount_smbfs //truenas_admin@truenas-ip/Projects /tmp/truenas
   cp youtube_credentials.json youtube_token.json /tmp/truenas/langflix/assets/
   umount /tmp/truenas
   ```
   
   **Or use TrueNAS Web UI:**
   - Web UI → **Storage** → **Pools** → `Pool_2/Projects/langflix/assets/`
   - Use file upload feature
   
   **Or use SSH/SCP:**
   ```bash
   scp youtube_credentials.json youtube_token.json \
       truenas_admin@truenas-ip:/mnt/Pool_2/Projects/langflix/assets/
   ```

4. **Adjust permissions so Docker containers can access them (UID/GID 1000).**
   
   **On TrueNAS:**
   ```bash
   cd /mnt/Pool_2/Projects/langflix/assets
   
   # Change file ownership
   sudo chown 1000:1000 youtube_credentials.json youtube_token.json
   
   # Set file permissions
   # youtube_credentials.json: read-only (644)
   sudo chmod 644 youtube_credentials.json
   
   # youtube_token.json: read/write (600, more secure)
   sudo chmod 600 youtube_token.json
   
   # Verify permissions
   ls -la youtube_*.json
   # Expected output:
   # -rw-r--r-- 1 1000 1000 youtube_credentials.json
   # -rw------- 1 1000 1000 youtube_token.json
   ```

5. **Test file access from inside container:**
   ```bash
   # Test after starting containers
   sudo docker exec langflix-ui cat /app/youtube_credentials.json | head -5
   sudo docker exec langflix-ui ls -la /app/youtube_*.json
   ```
   
   If you get `Permission denied` error:
   - Verify file ownership is `1000:1000`
   - Verify file permissions are correct (`644` or `600`)
   - Check if TrueNAS ACL is blocking permissions

6. The compose file mounts these files into the UI container automatically (read-only for credentials, writable for token).
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

### Method 1: Use run.sh Script (Recommended)

The `deploy/run.sh` script automatically handles directory creation, permission setting, and Docker Compose startup.

```bash
cd /mnt/Pool_2/Projects/langflix/deploy

# Grant execute permission (first time only)
chmod +x run.sh shutdown.sh

# Start
./run.sh
```

The script automatically:
- Checks `.env` file
- Creates required directories (`output`, `logs`, `cache`, `assets`, `db-backups`)
- Sets directory permissions (UID/GID 1000:1000)
- Verifies YouTube credential files
- Starts Docker Compose
- Checks container status

### Method 2: Manual Execution

**Default Method (Recommended):** Use `sudo` with `truenas_admin` account

```bash
cd /mnt/Pool_2/Projects/langflix/deploy

# Pull or build images
sudo docker compose -f docker-compose.truenas.yml pull
# or
sudo docker compose -f docker-compose.truenas.yml build

# Start stack
sudo docker compose -f docker-compose.truenas.yml up -d

# Verify
sudo docker compose -f docker-compose.truenas.yml ps
```

> **Note:** In TrueNAS SCALE, the Docker socket is owned by root, so you must use `sudo` when running commands as `truenas_admin`. Some systems may have the `apps` user disabled, so using `sudo` is recommended.

**Alternative (Optional):** Use `apps` user (only if enabled on your system)

```bash
# Switch to apps user (only works if enabled on your system)
sudo -iu apps
cd /mnt/Pool_2/Projects/langflix/deploy
docker compose -f docker-compose.truenas.yml up -d
```

> **Warning:** If you get "currently not available" error with `apps` user, the system administrator needs to enable that user. In most cases, using `sudo` is simpler.

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

**Method 1: Use shutdown.sh Script (Recommended)**

```bash
cd /mnt/Pool_2/Projects/langflix/deploy

# Stop containers only (preserves volumes)
./shutdown.sh

# Remove volumes too (reset Redis data)
./shutdown.sh --remove-volumes

# Remove images too (force rebuild)
./shutdown.sh --remove-volumes --remove-images
```

**Method 2: Manual Execution**

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

### Directory Creation Permission Error (`chmod: operation not permitted`)

**Symptom:**
```
Error response from daemon: error while creating mount source path '/mnt/Pool_2/Projects/langflix/output': chmod /mnt/Pool_2/Projects/langflix/output: operation not permitted
```

**Cause:**
- Docker Compose attempts to automatically create directories for volume mounts, but TrueNAS ACLs cause permission setting to fail.
- Even if directories already exist, incorrect ownership can cause the same error.

**Solution:**

1. **Create required directories beforehand and set permissions:**
   ```bash
   cd /mnt/Pool_2/Projects/langflix
   
   # Create directories
   sudo mkdir -p output logs cache assets db-backups
   
   # Change ownership (important!)
   sudo chown -R 1000:1000 output logs cache assets db-backups
   
   # Set permissions
   sudo chmod -R 755 output logs cache assets db-backups
   
   # Verify permissions
   ls -la | grep -E "output|logs|cache|assets|db-backups"
   # Expected output:
   # drwxr-xr-x 1 1000 1000 output
   # drwxr-xr-x 1 1000 1000 logs
   # ...
   ```

2. **If `chmod`/`chown` doesn't work due to TrueNAS ACLs:**
   
   **Method A: Use TrueNAS Web UI (Recommended)**
   - Web UI → **Storage** → **Pools** → select dataset
   - Click **Permissions**
   - For each directory:
     - **User**: Select `1000` or `apps`
     - **Group**: Select `1000`
     - **Mode**: Set `755`
     - Click **Apply**
   
   **Method B: Use midclt Command**
   ```bash
   sudo midclt call filesystem.setperm path=/mnt/Pool_2/Projects/langflix/output mode=755 user=1000 group=1000
   sudo midclt call filesystem.setperm path=/mnt/Pool_2/Projects/langflix/logs mode=755 user=1000 group=1000
   sudo midclt call filesystem.setperm path=/mnt/Pool_2/Projects/langflix/cache mode=755 user=1000 group=1000
   sudo midclt call filesystem.setperm path=/mnt/Pool_2/Projects/langflix/assets mode=755 user=1000 group=1000
   sudo midclt call filesystem.setperm path=/mnt/Pool_2/Projects/langflix/db-backups mode=755 user=1000 group=1000
   ```
   
   > **Note:** If `midclt` command doesn't work, use TrueNAS web UI or contact your system administrator.

3. **After completing Step 5, restart Docker Compose:**
   ```bash
   cd /mnt/Pool_2/Projects/langflix/deploy
   sudo docker compose -f docker-compose.truenas.yml down
   sudo docker compose -f docker-compose.truenas.yml up -d
   ```

4. **Use run.sh script:**
   - The `run.sh` script automatically handles directory creation and permission setting.
   ```bash
   cd /mnt/Pool_2/Projects/langflix/deploy
   ./run.sh
   ```

### .env file permission error (`Permission denied: '/app/.env'`)

**Symptom:**
```
Error: [Errno 13] Permission denied: '/app/.env'
```

**Solution:**

> **Note:** In the latest version of `docker-compose.truenas.yml`, the `.env` file is not mounted into containers. All environment variables are passed directly via the `environment` section, so this error should not occur.

If you encounter this error:

1. **Verify you're using the latest `docker-compose.truenas.yml` file:**
   - Check that the `.env` file mount line is removed (should not have `- ../.env:/app/.env:ro` line)
   - Ensure you've copied the latest code to TrueNAS

2. **Restart containers:**
   ```bash
   sudo docker compose -f docker-compose.truenas.yml down
   sudo docker compose -f docker-compose.truenas.yml up -d
   ```

### Containers will not start
- Inspect Compose logs: `sudo docker compose -f docker-compose.truenas.yml logs`
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

### Media Path Not Accessible (`Permission denied`)

**Symptom:**
```bash
sudo docker exec langflix-api ls -lah /media/shows
# ls: cannot open directory '/media/shows': Permission denied
```

**Solution:**

1. **Verify and set media path permissions:**
   ```bash
   # Verify actual media path (e.g., /mnt/Pool_2/Media/Shows/Suits)
   MEDIA_PATH="/mnt/Pool_2/Media/Shows/Suits"  # Change to your actual path
   
   # Set permissions
   sudo chown -R 1000:1000 "$MEDIA_PATH"
   sudo chmod -R 755 "$MEDIA_PATH"
   
   # Verify permissions
   ls -la "$MEDIA_PATH" | head -5
   ```

2. **Test access from inside container:**
   ```bash
   sudo docker exec langflix-api ls -lah /media/shows
   # If file list appears, success
   ```

3. **If TrueNAS ACL is the issue:**
   - Web UI → **Storage** → select dataset → **Permissions**
   - For media path, set User `1000`, Group `1000`, Mode `755`
   - Or use `midclt` command:
     ```bash
     sudo midclt call filesystem.setperm path=/mnt/Pool_2/Media/Shows/Suits mode=755 user=1000 group=1000
     ```

4. **Verify `TRUENAS_MEDIA_PATH` in `.env`:**
   - Specify parent directory of actual media files
   - Example: `/mnt/Pool_2/Media` (actual files are in `/mnt/Pool_2/Media/Shows/Suits`)

### UI Logs Show PostgreSQL Connection Refused
- This happens when `DATABASE_ENABLED=false` (default) and the PostgreSQL service is not running.
- If you need database-backed features (quota tracking, scheduler, etc.), set `DATABASE_ENABLED=true` in `.env` and start the database profile:
  ```bash
  sudo docker compose -f docker-compose.truenas.yml --profile database up -d
  ```
- Otherwise, the warnings can be ignored.

### YouTube Credential File Access Error (`Permission denied`)

**Symptom:**
```bash
sudo docker exec langflix-ui cat /app/youtube_credentials.json | head -5
# cat: /app/youtube_credentials.json: Permission denied
```

**Solution:**

1. **Verify file ownership:**
   ```bash
   ls -la /mnt/Pool_2/Projects/langflix/assets/youtube_*.json
   # Expected output:
   # -rwxrwx--- 1 changik root youtube_credentials.json  # Wrong ownership
   # -rw-r--r-- 1 1000 1000 youtube_credentials.json      # Correct ownership
   ```

2. **Set file ownership and permissions:**
   ```bash
   cd /mnt/Pool_2/Projects/langflix/assets
   
   # Change ownership
   sudo chown 1000:1000 youtube_credentials.json youtube_token.json
   
   # Set permissions
   sudo chmod 644 youtube_credentials.json  # read-only
   sudo chmod 600 youtube_token.json        # read/write (more secure)
   
   # Verify
   ls -la youtube_*.json
   # Expected output:
   # -rw-r--r-- 1 1000 1000 youtube_credentials.json
   # -rw------- 1 1000 1000 youtube_token.json
   ```

3. **Test access from inside container:**
   ```bash
   # Restart container
   sudo docker compose -f docker-compose.truenas.yml restart langflix-ui
   
   # Test file access
   sudo docker exec langflix-ui cat /app/youtube_credentials.json | head -5
   sudo docker exec langflix-ui ls -la /app/youtube_*.json
   ```

4. **If TrueNAS ACL is the issue:**
   - Web UI → **Storage** → select dataset → **Permissions**
   - For `assets/youtube_credentials.json` file, set User `1000`, Group `1000`, Mode `644`
   - For `assets/youtube_token.json` file, set User `1000`, Group `1000`, Mode `600`
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

