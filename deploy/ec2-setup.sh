#!/bin/bash
# LangFlix EC2 Setup Script

set -e

echo "🚀 Setting up LangFlix on EC2..."

# Update system
sudo apt update && sudo apt upgrade -y

# Install system dependencies
sudo apt install -y \
    python3.9 \
    python3.9-pip \
    python3.9-venv \
    ffmpeg \
    git \
    htop \
    unzip

# Create langflix user
sudo useradd -m -s /bin/bash langflix
sudo usermod -aG sudo langflix

# Create application directory
sudo mkdir -p /opt/langflix
sudo chown langflix:langflix /opt/langflix

# Setup EBS volume mount point (assuming /dev/xvdf is attached)
sudo mkdir -p /data
# Uncomment after EBS volume is attached:
# sudo mkfs -t ext4 /dev/xvdf
# echo '/dev/xvdf /data ext4 defaults,nofail 0 2' | sudo tee -a /etc/fstab
# sudo mount -a
sudo mkdir -p /data/langflix
sudo chown langflix:langflix /data/langflix

# Switch to langflix user for app setup
sudo -u langflix bash << 'EOF'
cd /opt/langflix

# Clone repository (replace with your actual repo)
git clone https://github.com/taigi0315/study_english_with_sutis.git .

# Create virtual environment
python3.9 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create directory structure
mkdir -p /data/langflix/{assets,output,logs}
mkdir -p assets/media
mkdir -p assets/subtitles

# Copy configuration files
cp env.example .env
cp config.example.yaml config.yaml

echo "✅ LangFlix installation completed!"
echo "📝 Next steps:"
echo "1. Edit /opt/langflix/.env with your GEMINI_API_KEY"
echo "2. Mount your video files to /data/langflix/assets/media"
echo "3. Run: /opt/langflix/venv/bin/python -m langflix.main --help"
EOF

# Create systemd service
sudo tee /etc/systemd/system/langflix.service > /dev/null << 'EOF'
[Unit]
Description=LangFlix Video Processing Service
After=network.target

[Service]
Type=simple
User=langflix
Group=langflix
WorkingDirectory=/opt/langflix
Environment=PATH=/opt/langflix/venv/bin
ExecStart=/opt/langflix/venv/bin/python -m langflix.main --subtitle %i
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Enable service
sudo systemctl daemon-reload
sudo systemctl enable langflix.service

echo "🎉 Setup completed!"
echo "📋 Service management:"
echo "  sudo systemctl start langflix.service"
echo "  sudo systemctl status langflix.service"
echo "  sudo journalctl -u langflix.service -f"
