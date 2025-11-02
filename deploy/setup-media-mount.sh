#!/bin/bash
# Setup network media mount for Docker
# Usage: ./setup-media-mount.sh [nfs|cifs] [server_ip] [share_path] [mount_point]

set -e

# Default values
MOUNT_TYPE="${1:-nfs}"
MEDIA_SERVER="${2:-192.168.86.43}"
MEDIA_SHARE="${3:-/media/shows}"
MOUNT_POINT="${4:-/mnt/media-server}"

echo "=== LangFlix Network Media Mount Setup ==="
echo "Type: ${MOUNT_TYPE}"
echo "Server: ${MEDIA_SERVER}"
echo "Share: ${MEDIA_SHARE}"
echo "Mount Point: ${MOUNT_POINT}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Error: Please run as root (use sudo)"
    exit 1
fi

# Create mount point
echo "Creating mount point: ${MOUNT_POINT}"
mkdir -p "${MOUNT_POINT}"

# Test network connectivity
echo "Testing network connectivity to ${MEDIA_SERVER}..."
if ! ping -c 1 -W 2 "${MEDIA_SERVER}" > /dev/null 2>&1; then
    echo "Warning: Cannot ping ${MEDIA_SERVER}. Continuing anyway..."
fi

# Mount based on type
case "${MOUNT_TYPE}" in
    nfs)
        echo "Setting up NFS mount..."
        
        # Check if nfs-common is installed
        if ! command -v mount.nfs &> /dev/null; then
            echo "Installing nfs-common..."
            if command -v apt-get &> /dev/null; then
                apt-get update && apt-get install -y nfs-common
            elif command -v yum &> /dev/null; then
                yum install -y nfs-utils
            else
                echo "Error: Cannot detect package manager. Please install nfs-common/nfs-utils manually."
                exit 1
            fi
        fi
        
        # Try to mount
        echo "Mounting ${MEDIA_SERVER}:${MEDIA_SHARE} to ${MOUNT_POINT}..."
        if mount -t nfs "${MEDIA_SERVER}:${MEDIA_SHARE}" "${MOUNT_POINT}"; then
            echo "✓ Successfully mounted NFS share"
        else
            echo "✗ Failed to mount NFS share"
            exit 1
        fi
        
        # Add to /etc/fstab if not already present
        FSTAB_ENTRY="${MEDIA_SERVER}:${MEDIA_SHARE} ${MOUNT_POINT} nfs defaults 0 0"
        if ! grep -q "${MOUNT_POINT}" /etc/fstab; then
            echo "Adding entry to /etc/fstab..."
            echo "${FSTAB_ENTRY}" >> /etc/fstab
            echo "✓ Added to /etc/fstab"
        else
            echo "✓ Entry already exists in /etc/fstab"
        fi
        ;;
        
    cifs)
        echo "Setting up CIFS/SMB mount..."
        
        # Check if cifs-utils is installed
        if ! command -v mount.cifs &> /dev/null; then
            echo "Installing cifs-utils..."
            if command -v apt-get &> /dev/null; then
                apt-get update && apt-get install -y cifs-utils
            elif command -v yum &> /dev/null; then
                yum install -y cifs-utils
            else
                echo "Error: Cannot detect package manager. Please install cifs-utils manually."
                exit 1
            fi
        fi
        
        # Get credentials
        read -p "Enter username for ${MEDIA_SERVER}: " USERNAME
        read -sp "Enter password: " PASSWORD
        echo ""
        
        # Create credentials file
        CREDS_FILE="/etc/cifs-credentials"
        echo "Creating credentials file: ${CREDS_FILE}"
        cat > "${CREDS_FILE}" << EOF
username=${USERNAME}
password=${PASSWORD}
EOF
        chmod 600 "${CREDS_FILE}"
        
        # Get current user UID/GID
        CURRENT_UID=$(id -u)
        CURRENT_GID=$(id -g)
        
        # Try to mount
        echo "Mounting //${MEDIA_SERVER}${MEDIA_SHARE} to ${MOUNT_POINT}..."
        if mount -t cifs "//${MEDIA_SERVER}${MEDIA_SHARE}" "${MOUNT_POINT}" \
            -o credentials="${CREDS_FILE},uid=${CURRENT_UID},gid=${CURRENT_GID}"; then
            echo "✓ Successfully mounted CIFS share"
        else
            echo "✗ Failed to mount CIFS share"
            rm -f "${CREDS_FILE}"
            exit 1
        fi
        
        # Add to /etc/fstab if not already present
        FSTAB_ENTRY="//${MEDIA_SERVER}${MEDIA_SHARE} ${MOUNT_POINT} cifs credentials=${CREDS_FILE},uid=${CURRENT_UID},gid=${CURRENT_GID} 0 0"
        if ! grep -q "${MOUNT_POINT}" /etc/fstab; then
            echo "Adding entry to /etc/fstab..."
            echo "${FSTAB_ENTRY}" >> /etc/fstab
            echo "✓ Added to /etc/fstab"
        else
            echo "✓ Entry already exists in /etc/fstab"
        fi
        ;;
        
    *)
        echo "Error: Unknown mount type '${MOUNT_TYPE}'. Use 'nfs' or 'cifs'."
        exit 1
        ;;
esac

# Verify mount
echo ""
echo "Verifying mount..."
if mountpoint -q "${MOUNT_POINT}"; then
    echo "✓ Mount point is active: ${MOUNT_POINT}"
    echo ""
    echo "Directory contents:"
    ls -la "${MOUNT_POINT}" | head -10
    echo ""
    echo "✓ Setup complete!"
    echo ""
    echo "Next steps:"
    echo "1. Update docker-compose.media-server.yml to use: - ${MOUNT_POINT}:/media/shows:ro"
    echo "2. Set environment variable: LANGFLIX_STORAGE_LOCAL_BASE_PATH=/media/shows"
    echo "3. Start Docker container: docker-compose -f deploy/docker-compose.media-server.yml up -d"
else
    echo "✗ Mount point verification failed"
    exit 1
fi

