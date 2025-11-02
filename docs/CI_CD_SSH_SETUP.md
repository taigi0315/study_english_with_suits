# CI/CD SSH Key Setup for TrueNAS Deployment

This guide explains how to set up SSH keys for automated deployment from GitHub Actions to TrueNAS.

## Overview

The CI/CD pipeline can automatically deploy to TrueNAS using SSH. This requires:
1. SSH key pair generation
2. Public key on TrueNAS server
3. Private key in GitHub Secrets
4. GitHub repository secrets configuration

## Step 1: Generate SSH Key Pair

On your local machine or CI/CD server, generate an SSH key pair:

```bash
# Generate SSH key pair (no passphrase for automated deployment)
ssh-keygen -t ed25519 -C "github-actions-truenas-deploy" -f ~/.ssh/github_actions_truenas

# This creates:
# - ~/.ssh/github_actions_truenas (private key)
# - ~/.ssh/github_actions_truenas.pub (public key)
```

**Important:** 
- Don't use a passphrase (leave empty) for automated deployments
- Keep the private key secure - never commit it to git
- Store the private key in GitHub Secrets

## Step 2: Add Public Key to TrueNAS

### Option A: Using SSH (Recommended)

1. Copy the public key:
   ```bash
   cat ~/.ssh/github_actions_truenas.pub
   ```

2. SSH into TrueNAS and add to authorized_keys:
   ```bash
   ssh admin@truenas
   
   # Create .ssh directory if it doesn't exist
   mkdir -p ~/.ssh
   chmod 700 ~/.ssh
   
   # Add public key to authorized_keys
   echo "YOUR_PUBLIC_KEY_HERE" >> ~/.ssh/authorized_keys
   chmod 600 ~/.ssh/authorized_keys
   ```

3. Test SSH connection:
   ```bash
   ssh -i ~/.ssh/github_actions_truenas admin@truenas
   ```

### Option B: Using TrueNAS Web UI

1. Navigate to **Credentials** → **SSH Keypairs**
2. Click **Add**
3. Paste the public key content
4. Save

## Step 3: Add Private Key to GitHub Secrets

1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**

Add these secrets:

### Required Secrets

1. **TRUENAS_HOST**
   - Name: `TRUENAS_HOST`
   - Value: Your TrueNAS server IP or hostname
   - Example: `192.168.1.100` or `truenas.local`

2. **TRUENAS_USER**
   - Name: `TRUENAS_USER`
   - Value: SSH username (usually `admin` or `root`)
   - Example: `admin`

3. **TRUENAS_SSH_KEY**
   - Name: `TRUENAS_SSH_KEY`
   - Value: Contents of the **private key** file
   - Example:
     ```
     -----BEGIN OPENSSH PRIVATE KEY-----
     b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
     ...
     -----END OPENSSH PRIVATE KEY-----
     ```
   - **Important:** Copy the entire private key including headers

## Step 4: Enable Deploy Job in CI/CD

The deploy job is currently commented out in `.github/workflows/ci.yml`. To enable it:

1. Uncomment the deploy job section:
   ```yaml
   deploy:
     name: Deploy to TrueNAS
     needs: [build-and-push, security-scan]
     runs-on: ubuntu-latest
     if: github.ref == 'refs/heads/main' && github.event_name == 'push'
     environment: production
     
     steps:
       - uses: actions/checkout@v4
       
       - name: Deploy to TrueNAS
         uses: appleboy/ssh-action@master
         with:
           host: ${{ secrets.TRUENAS_HOST }}
           username: ${{ secrets.TRUENAS_USER }}
           key: ${{ secrets.TRUENAS_SSH_KEY }}
           script: |
             cd /mnt/pool/apps/langflix/deploy
             docker-compose -f docker-compose.truenas.yml pull
             docker-compose -f docker-compose.truenas.yml up -d
             docker system prune -af --volumes
   ```

2. Optionally, add a GitHub Environment for production:
   - Go to **Settings** → **Environments** → **New environment**
   - Name: `production`
   - Add protection rules if needed (required reviewers, wait timer)

## Step 5: Test Deployment

1. Push to main branch
2. Check GitHub Actions workflow runs
3. Verify deploy job executes successfully
4. SSH into TrueNAS and verify containers are running:
   ```bash
   ssh admin@truenas
   cd /mnt/pool/apps/langflix/deploy
   docker-compose -f docker-compose.truenas.yml ps
   ```

## Security Best Practices

### 1. Use Dedicated SSH Key
- Don't reuse personal SSH keys
- Use a key specifically for CI/CD automation
- Rotate keys periodically

### 2. Restrict SSH Access
On TrueNAS server, configure SSH to be more secure:

```bash
# Edit SSH config
sudo nano /etc/ssh/sshd_config

# Recommended settings:
PermitRootLogin no
PasswordAuthentication no  # Only key-based auth
PubkeyAuthentication yes
AuthorizedKeysFile .ssh/authorized_keys
```

### 3. Use SSH Agent Forwarding (Alternative)

If you prefer, you can use SSH agent forwarding instead of storing the private key:

```yaml
- name: Deploy to TrueNAS
  uses: appleboy/ssh-action@master
  with:
    host: ${{ secrets.TRUENAS_HOST }}
    username: ${{ secrets.TRUENAS_USER }}
    # Use SSH agent instead of key
    use_insecure_cipher: false
    # ... other options
```

However, this requires additional setup and the private key method is simpler for automation.

### 4. Monitor SSH Access

Check SSH access logs on TrueNAS:
```bash
# View recent SSH connections
sudo tail -f /var/log/auth.log

# Check failed login attempts
sudo grep "Failed password" /var/log/auth.log
```

### 5. Rotate Keys Regularly

- Rotate SSH keys every 90 days
- Remove old keys from authorized_keys
- Update GitHub Secrets with new key

## Troubleshooting

### SSH Connection Fails

**Error:** `Permission denied (publickey)`

**Solutions:**
1. Verify public key is in `~/.ssh/authorized_keys` on TrueNAS
2. Check file permissions: `chmod 600 ~/.ssh/authorized_keys`
3. Verify private key in GitHub Secrets is complete (including headers)
4. Test SSH manually: `ssh -i ~/.ssh/github_actions_truenas admin@truenas`

### Key Format Issues

**Error:** `invalid private key`

**Solutions:**
1. Ensure private key includes BEGIN/END headers
2. Copy entire key including newlines
3. Use OpenSSH format (not PuTTY .ppk)

### Permission Denied on Deployment Script

**Error:** `Permission denied` when running docker-compose

**Solutions:**
1. Ensure SSH user has Docker permissions:
   ```bash
   sudo usermod -aG docker $USER
   ```
2. Or use sudo in deployment script:
   ```yaml
   script: |
     cd /mnt/pool/apps/langflix/deploy
     sudo docker-compose -f docker-compose.truenas.yml pull
     sudo docker-compose -f docker-compose.truenas.yml up -d
   ```

## Alternative: Manual Deployment

If you prefer manual deployment or don't want to set up SSH keys:

1. Keep deploy job commented out in CI/CD
2. After CI/CD builds and pushes images, manually deploy:
   ```bash
   ssh admin@truenas
   cd /mnt/pool/apps/langflix/deploy
   docker-compose -f docker-compose.truenas.yml pull
   docker-compose -f docker-compose.truenas.yml up -d
   ```

Or use a webhook-based deployment system instead of SSH.

## Summary

**What you need:**
1. SSH key pair (public + private)
2. Public key on TrueNAS server
3. Three GitHub Secrets:
   - `TRUENAS_HOST` (IP/hostname)
   - `TRUENAS_USER` (username)
   - `TRUENAS_SSH_KEY` (private key)

**When configured:**
- CI/CD will automatically deploy to TrueNAS on push to main
- Deploy job runs after build and security scan
- Containers are updated and restarted automatically


