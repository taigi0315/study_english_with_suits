# LangFlix Setup Guide for Dockge

## Overview

Guide for running LangFlix in Docker using Dockge on TrueNAS.

## Prerequisites

1. Dockge installed on TrueNAS
2. Media file path confirmed (how `192.168.86.43/media/shows` is mounted on TrueNAS)
3. Docker image built or pulled from registry

## Step-by-Step Setup

### Step 1: Confirm Media Path

Check media path in TrueNAS shell:

```bash
# After accessing TrueNAS shell
ls -la /mnt/

# Find media path (examples)
# /mnt/pool/media/shows or
# /mnt/tank/media/shows or
# /mnt/media-server
```

### Step 2: Prepare Project

**Option A: Clone from Git (Recommended)**
```bash
cd /mnt/pool/apps/  # or desired path
git clone <your-repo-url> langflix
cd langflix
```

**Option B: Direct File Upload**
- Upload files via TrueNAS web UI
- Or upload via SMB/NFS share

### Step 3: Build Docker Image (Optional)

If not using build in Dockge, pre-build the image:

```bash
cd /path/to/langflix
docker build -f Dockerfile.dev -t langflix:latest .
```

### Step 4: Create Stack in Dockge

1. **Access Dockge Web UI**
   - Open browser: `http://192.168.86.43:31014`

2. **Create New Stack**
   - Click "+ Compose" in left sidebar
   - Or select existing stack

3. **Enter Stack Name**
   - Stack Name: `langflix` (lowercase only)

4. **Enter Following Content in YAML Editor**

```yaml
services:
  langflix:
    # Use image (if pre-built)
    image: langflix:latest
    
    # Or use build (if Dockge supports)
    # build:
    #   context: /mnt/pool/apps/langflix
    #   dockerfile: Dockerfile.dev
    
    container_name: langflix-app
    restart: unless-stopped
    
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - LANGFLIX_LOG_LEVEL=INFO
      - LANGFLIX_STORAGE_LOCAL_BASE_PATH=/media/shows
    
    volumes:
      # Change to actual media path on TrueNAS
      - /mnt/pool/media/shows:/media/shows:ro
      
      # Config file
      - /mnt/pool/apps/langflix/config.yaml:/app/config.yaml:ro
      
      # Output directory
      - /mnt/pool/apps/langflix/output:/data/output
    
    ports:
      - "8000:8000"
      - "5000:5000"
    
    deploy:
      resources:
        limits:
          memory: 8G
          cpus: '4'
    
    healthcheck:
      test: ["CMD", "python", "-c", "import langflix; print('OK')"]
      interval: 30s
      timeout: 10s
      retries: 3
```

5. **Set Environment Variables (.env Section)**

Add to Dockge's ".env" section:

```bash
# Gemini API Key (Required)
GEMINI_API_KEY=your_gemini_api_key_here
```

### Step 5: Verify and Modify Paths

**Important**: Must change following paths to actual TrueNAS paths:

1. **Media Path**: 
   ```yaml
   volumes:
     - /mnt/pool/media/shows:/media/shows:ro
   ```
   → Check where `192.168.86.43/media/shows` is actually mounted on TrueNAS

2. **Config File Path**:
   ```yaml
   - /mnt/pool/apps/langflix/config.yaml:/app/config.yaml:ro
   ```
   → Change to actual project path

3. **Output Directory**:
   ```yaml
   - /mnt/pool/apps/langflix/output:/data/output
   ```
   → Path to store generated files

### Step 6: Deploy

1. Click **"Deploy"** button in Dockge
2. Check logs (Console tab)
3. Verify status: Should show `active`

### Step 7: Verify Access

```bash
# API Documentation
http://192.168.86.43:8000/docs

# API Status Check
http://192.168.86.43:8000/

# Frontend (if using)
http://192.168.86.43:5000
```

## Finding TrueNAS Paths

### Method 1: Check in Web UI
1. Access TrueNAS web UI
2. Storage → Pools menu
3. Check pool name (e.g., `pool`, `tank`, `storage`)

### Method 2: Check in Shell
```bash
# In TrueNAS shell
df -h | grep media

# Or
mount | grep media

# Check all mount points
ls -la /mnt/
```

### Method 3: Check SMB/NFS Share Paths
- Check share paths in TrueNAS Shares → SMB or NFS
- Actual filesystem paths are usually `/mnt/<pool>/<dataset>/...` format

## Common TrueNAS Path Patterns

```yaml
volumes:
  # Pattern 1: Default pool
  - /mnt/pool/media/shows:/media/shows:ro
  
  # Pattern 2: tank pool
  - /mnt/tank/media/shows:/media/shows:ro
  
  # Pattern 3: storage pool
  - /mnt/storage/media/shows:/media/shows:ro
  
  # Pattern 4: ix-apps dataset (TrueNAS Scale)
  - /mnt/pool/ix-apps/docker-data:/media/shows:ro
```

## Troubleshooting

### Container Won't Start

**Check:**
```bash
# Check logs in Dockge Console
# Or in TrueNAS shell
docker logs langflix-app
```

**Common Issues:**
1. Path doesn't exist → Create directory or modify path
2. Permission issue → Check and fix permissions
3. Image not found → Build or pull image

### Cannot Find Media Files

**Check:**
```bash
# Check inside container
docker exec langflix-app ls -la /media/shows

# Check on host
ls -la /mnt/pool/media/shows
```

**Solution:**
- Verify volume mount path is correct
- Check read permissions
- Verify media server path is actually mounted on TrueNAS

### Environment Variables Not Applied

**Using .env file:**
```bash
# In Dockge's .env section
GEMINI_API_KEY=your_key_here
```

**Or set directly:**
```yaml
environment:
  - GEMINI_API_KEY=your_key_here
```

## Optimization Tips

1. **Read-only Mounts**: Use `:ro` flag for media files
2. **Resource Limits**: Adjust based on TrueNAS capabilities
3. **Log Management**: Mount log directory for log file management
4. **Network Settings**: Use Dockge's External Networks to communicate with other apps

## Next Steps

1. Check API docs: `http://192.168.86.43:8000/docs`
2. Test media file processing
3. Set up monitoring
4. Create automation scripts

## References

- Full Docker Compose example: `deploy/docker-compose.dockge.yml`
- Network media setup: `docs/deployment/DOCKER_NETWORK_MEDIA_eng.md`
- API documentation: `docs/api/README_eng.md`

