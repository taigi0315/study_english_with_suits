# Docker Network Media Path Configuration

## Overview

This guide explains how to configure LangFlix Docker containers to access media files stored on a network server (e.g., `192.168.86.43/media/shows/suits`).

## Prerequisites

- Network server accessible from Docker host
- Network share configured (NFS, CIFS/SMB, or already mounted)
- Docker and docker-compose installed

## Approach Options

### Option 1: Mount Network Path on Host (Recommended)

Mount the network share on the Docker host first, then mount it into the container.

#### Step 1: Mount Network Share on Host

**For NFS:**
```bash
# Install NFS client (if not already installed)
sudo apt-get install nfs-common  # Ubuntu/Debian
# or
sudo yum install nfs-utils       # CentOS/RHEL

# Create mount point
sudo mkdir -p /mnt/media-server

# Mount NFS share
sudo mount -t nfs 192.168.86.43:/media/shows /mnt/media-server

# Make permanent (add to /etc/fstab)
echo "192.168.86.43:/media/shows /mnt/media-server nfs defaults 0 0" | sudo tee -a /etc/fstab
```

**For CIFS/SMB (Windows share):**
```bash
# Install CIFS utilities
sudo apt-get install cifs-utils  # Ubuntu/Debian
# or
sudo yum install cifs-utils      # CentOS/RHEL

# Create mount point
sudo mkdir -p /mnt/media-server

# Mount CIFS share (with credentials)
sudo mount -t cifs //192.168.86.43/media /mnt/media-server \
    -o username=your_user,password=your_password,uid=$(id -u),gid=$(id -g)

# Make permanent (add to /etc/fstab)
# Create credentials file
sudo bash -c 'cat > /etc/cifs-credentials << EOF
username=your_user
password=your_password
EOF'
sudo chmod 600 /etc/cifs-credentials

# Add to /etc/fstab
echo "//192.168.86.43/media /mnt/media-server cifs credentials=/etc/cifs-credentials,uid=$(id -u),gid=$(id -g) 0 0" | sudo tee -a /etc/fstab
```

#### Step 2: Configure Docker Compose

Update `deploy/docker-compose.media-server.yml`:

```yaml
services:
  langflix-media:
    volumes:
      # Mount the host-mounted network path
      - /mnt/media-server:/media/shows:ro  # Read-only for safety
```

#### Step 3: Configure Application

Set storage path via environment variable:

```bash
# In docker-compose.yml or .env file
LANGFLIX_STORAGE_LOCAL_BASE_PATH=/media/shows
```

Or update `config.yaml`:

```yaml
storage:
  backend: "local"
  local:
    base_path: "/media/shows"
```

### Option 2: Environment Variable Configuration

Use environment variables to configure the media path without modifying Dockerfile.

#### Docker Compose Example

```yaml
services:
  langflix-media:
    environment:
      - LANGFLIX_STORAGE_LOCAL_BASE_PATH=/media/shows
    volumes:
      - /mnt/media-server:/media/shows:ro
```

#### Run with Docker Run

```bash
docker run -d \
  -e LANGFLIX_STORAGE_LOCAL_BASE_PATH=/media/shows \
  -v /mnt/media-server:/media/shows:ro \
  langflix:latest
```

### Option 3: Build Argument (Less Flexible)

If you need the path at build time, use Dockerfile ARG:

```dockerfile
ARG MEDIA_PATH=/media/shows

RUN mkdir -p ${MEDIA_PATH}
ENV LANGFLIX_STORAGE_LOCAL_BASE_PATH=${MEDIA_PATH}
```

Build with:
```bash
docker build --build-arg MEDIA_PATH=/media/shows -t langflix:latest .
```

## Configuration Priority

LangFlix configuration priority (highest to lowest):
1. Environment variables (`LANGFLIX_STORAGE_LOCAL_BASE_PATH`)
2. `config.yaml` file (`storage.local.base_path`)
3. Default values

## Example: Complete Setup

### 1. Host Setup Script

Create `deploy/setup-media-mount.sh`:

```bash
#!/bin/bash
# Setup network media mount for Docker

MEDIA_SERVER="192.168.86.43"
MEDIA_SHARE="/media/shows"
MOUNT_POINT="/mnt/media-server"

# Create mount point
sudo mkdir -p ${MOUNT_POINT}

# Mount NFS share
sudo mount -t nfs ${MEDIA_SERVER}:${MEDIA_SHARE} ${MOUNT_POINT}

# Verify mount
if mountpoint -q ${MOUNT_POINT}; then
    echo "✓ Successfully mounted ${MEDIA_SERVER}:${MEDIA_SHARE} to ${MOUNT_POINT}"
    ls -la ${MOUNT_POINT}
else
    echo "✗ Failed to mount network share"
    exit 1
fi
```

### 2. Docker Compose Configuration

Use `deploy/docker-compose.media-server.yml`:

```yaml
version: '3.8'

services:
  langflix-media:
    build:
      context: ..
      dockerfile: deploy/Dockerfile.ec2.with-media
    environment:
      - LANGFLIX_STORAGE_LOCAL_BASE_PATH=/media/shows
    volumes:
      - /mnt/media-server:/media/shows:ro
      - ../config.yaml:/app/config.yaml:ro
      - ./output:/data/output
```

### 3. Verify Configuration

```bash
# Start container
docker-compose -f deploy/docker-compose.media-server.yml up -d

# Check if media path is accessible
docker exec langflix-media-app ls -la /media/shows

# Check configuration
docker exec langflix-media-app python -c "from langflix import settings; print(settings.get_storage_local_path())"
```

## Troubleshooting

### Issue: Permission Denied

**Problem:** Container can't access mounted files.

**Solution:**
```bash
# Check mount permissions
ls -la /mnt/media-server

# Adjust ownership or use bind mount with uid/gid
docker run -v /mnt/media-server:/media/shows:ro \
  --user $(id -u):$(id -g) \
  langflix:latest
```

### Issue: Network Share Not Accessible

**Problem:** Cannot mount network share.

**Solution:**
1. Verify network connectivity: `ping 192.168.86.43`
2. Check firewall rules
3. Verify share permissions on server
4. Test mount manually before Docker

### Issue: Slow Performance

**Problem:** Network I/O is slow.

**Solution:**
1. Use NFS instead of CIFS if possible
2. Increase NFS timeout values
3. Consider caching frequently accessed files
4. Use local storage for processing, copy results back

## Security Considerations

1. **Read-only mounts**: Use `:ro` flag for media volumes (prevents accidental writes)
2. **Network security**: Ensure network share is on trusted network or use VPN
3. **Credentials**: Store SMB/CIFS credentials securely (use credential files, not command line)
4. **Access control**: Limit network share access to necessary users only

## Best Practices

1. **Mount on host first**: More reliable and easier to debug
2. **Use environment variables**: Easier to change without rebuilding
3. **Read-only for media**: Media files should typically be read-only
4. **Separate output**: Keep generated files in separate volume
5. **Monitor disk space**: Network mounts can fill up local cache

## References

- Docker volumes: https://docs.docker.com/storage/volumes/
- NFS mounting: https://linux.die.net/man/8/mount.nfs
- CIFS mounting: https://linux.die.net/man/8/mount.cifs
- LangFlix Storage Documentation: `docs/storage/README_eng.md`

