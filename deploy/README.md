# LangFlix AWS EC2 Deployment Guide

This guide covers deploying LangFlix to AWS EC2 with S3 storage integration for scalable video processing.

## Architecture Overview

```
User → S3 (Input Bucket) → EC2 (Processing) → S3 (Output Bucket)
                              ↓
                         EBS (Temp Work)
```

## Prerequisites

- AWS Account with EC2 and S3 access
- AWS CLI configured (`aws configure`)
- Google Gemini API key
- Domain knowledge of AWS services

## Quick Start

### 1. Create S3 Buckets

```bash
# Create input bucket for videos and subtitles
aws s3 mb s3://langflix-input

# Create output bucket for processed videos
aws s3 mb s3://langflix-output

# Set appropriate permissions
aws s3api put-bucket-versioning --bucket langflix-input --versioning-configuration Status=Enabled
aws s3api put-bucket-versioning --bucket langflix-output --versioning-configuration Status=Enabled
```

### 2. Launch EC2 Instance

**Recommended Instance Configuration:**
- **Instance Type**: `c5.2xlarge` (8 vCPU, 16 GB RAM)
- **AMI**: Ubuntu 22.04 LTS
- **Storage**: 
  - Root volume: 50 GB gp3
  - Additional EBS volume: 500 GB gp3 (for temp processing)
- **Security Group**: 
  - SSH (22) from your IP
  - Optional: HTTP (80) for future web interface

**Launch Commands:**
```bash
# Create security group
aws ec2 create-security-group \
    --group-name langflix-sg \
    --description "LangFlix EC2 Security Group"

# Add SSH access (replace YOUR_IP with your actual IP)
aws ec2 authorize-security-group-ingress \
    --group-name langflix-sg \
    --protocol tcp \
    --port 22 \
    --cidr YOUR_IP/32

# Launch instance (replace key-pair-name with your key pair)
aws ec2 run-instances \
    --image-id ami-0c02fb55956c7d316 \
    --count 1 \
    --instance-type c5.2xlarge \
    --key-name your-key-pair-name \
    --security-groups langflix-sg \
    --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":50,"VolumeType":"gp3"}}]'
```

### 3. Setup EBS Volume

After instance is running:

```bash
# Create and attach EBS volume
aws ec2 create-volume \
    --size 500 \
    --volume-type gp3 \
    --availability-zone us-east-1a

# Attach volume to instance
aws ec2 attach-volume \
    --volume-id vol-xxxxxxxxx \
    --instance-id i-xxxxxxxxx \
    --device /dev/xvdf
```

### 4. Run Setup Script

**SSH into your instance:**
```bash
ssh -i your-key.pem ubuntu@YOUR_INSTANCE_IP
```

**Run the setup:**
```bash
# Download and run setup script
wget https://raw.githubusercontent.com/taigi0315/study_english_with_sutis/main/deploy/ec2-setup.sh
chmod +x ec2-setup.sh
sudo ./ec2-setup.sh
```

**Mount EBS volume:**
```bash
# Format and mount the EBS volume
sudo mkfs -t ext4 /dev/xvdf
sudo mkdir -p /data
sudo mount /dev/xvdf /data
echo '/dev/xvdf /data ext4 defaults,nofail 0 2' | sudo tee -a /etc/fstab
sudo chown -R langflix:langflix /data
```

### 5. Configure Application

**Set environment variables:**
```bash
sudo nano /opt/langflix/.env
```

Add the following:
```env
# Required API keys
GEMINI_API_KEY=your_gemini_api_key_here
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_DEFAULT_REGION=us-east-1

# Optional configuration
LANGFLIX_LOG_LEVEL=INFO
LANGFLIX_MAX_CONCURRENT_JOBS=4
```

**Configure S3 storage:**
```bash
sudo nano /opt/langflix/config.yaml
```

Update storage section:
```yaml
storage:
  backend: "s3"
  s3:
    input_bucket: "langflix-input"
    output_bucket: "langflix-output"
    region: "us-east-1"
    input_prefix: "videos/"
    output_prefix: "processed/"
  local:
    temp_dir: "/data/langflix/temp"
    assets_dir: "/data/langflix/assets"
    output_dir: "/data/langflix/output"
```

### 6. Test the Setup

**Upload test files to S3:**
```bash
# From your local machine
aws s3 cp test_video.mkv s3://langflix-input/videos/
aws s3 cp test_subtitle.srt s3://langflix-input/videos/
```

**Process video on EC2:**
```bash
# SSH into EC2 and run processing
sudo -u langflix /opt/langflix/venv/bin/python -m langflix.main \
  --subtitle s3://langflix-input/videos/test_subtitle.srt \
  --video-dir s3://langflix-input/videos/ \
  --output-dir /data/langflix/output
```

**Download results:**
```bash
# From your local machine
aws s3 sync s3://langflix-output/processed/ ./results/
```

## Advanced Configuration

### Performance Tuning

**Instance Types:**
- **Development**: `c5.large` (2 vCPU, 4 GB RAM)
- **Production**: `c5.2xlarge` (8 vCPU, 16 GB RAM) 
- **High Volume**: `c5.4xlarge` (16 vCPU, 32 GB RAM)

**EBS Configuration:**
- **Volume Type**: `gp3` (recommended) or `io2` for high IOPS
- **Size**: 500GB minimum for temp processing
- **IOPS**: 3000+ for better performance

### Monitoring and Logging

**CloudWatch Integration:**
```bash
# Install CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i amazon-cloudwatch-agent.deb
```

**Log Monitoring:**
```bash
# View LangFlix logs
sudo journalctl -u langflix.service -f

# View application logs
tail -f /opt/langflix/langflix.log
```

### Security Best Practices

1. **Use IAM Roles** instead of access keys when possible
2. **Enable S3 bucket encryption**
3. **Restrict security group access** to minimal required ports
4. **Regular security updates**: `sudo apt update && sudo apt upgrade`
5. **Regular backups** of configuration and logs

### Cost Optimization

1. **Use Spot Instances** for non-critical processing
2. **Auto-scaling** for variable workloads
3. **S3 Lifecycle policies** for old processed files
4. **Monitor and terminate** unused instances

## Troubleshooting

### Common Issues

**1. Permission Denied Error:**
```bash
sudo chown -R langflix:langflix /opt/langflix
sudo chown -R langflix:langflix /data
```

**2. AWS Credentials Error:**
```bash
# Check credentials
aws sts get-caller-identity

# Test S3 access
aws s3 ls s3://langflix-input/
```

**3. FFmpeg Not Found:**
```bash
# Reinstall ffmpeg
sudo apt update
sudo apt install ffmpeg
```

**4. Out of Disk Space:**
```bash
# Check disk usage
df -h
du -sh /data/langflix/temp/*

# Clean temporary files
sudo rm -rf /data/langflix/temp/*
```

### Log Analysis

**Application Logs:**
```bash
grep "ERROR" /opt/langflix/langflix.log
grep "S3" /opt/langflix/langflix.log | tail -20
```

**System Logs:**
```bash
sudo journalctl -u langflix.service --since "1 hour ago"
```

## Scaling Considerations

### Horizontal Scaling
- Use SQS for job queuing
- Multiple EC2 instances with Auto Scaling
- Load balancer for web interface (future)

### Vertical Scaling
- Increase instance size for larger videos
- Add more EBS volumes for parallel processing
- Use GPU instances for advanced video processing

## Support and Maintenance

### Regular Maintenance Tasks
1. **Weekly**: Monitor disk usage and clean temp files
2. **Monthly**: Update system packages and security patches
3. **Quarterly**: Review and optimize costs

### Backup Strategy
1. **Configuration**: Backup `/opt/langflix/config.yaml` and `.env`
2. **Logs**: Archive important log files to S3
3. **Code**: Use git tags for version tracking

---

For additional support, check the main project documentation or create an issue in the repository.
