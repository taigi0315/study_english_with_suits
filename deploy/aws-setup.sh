#!/bin/bash

# LangFlix AWS Resource Setup Script
# This script creates the necessary AWS resources for LangFlix deployment

set -e

# Configuration
REGION=${AWS_DEFAULT_REGION:-us-east-1}
INPUT_BUCKET=${INPUT_BUCKET:-langflix-input}
OUTPUT_BUCKET=${OUTPUT_BUCKET:-langflix-output}
KEY_PAIR_NAME=${KEY_PAIR_NAME:-}
INSTANCE_TYPE=${INSTANCE_TYPE:-c5.2xlarge}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

echo_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

echo_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if AWS CLI is installed and configured
check_aws_cli() {
    echo_info "Checking AWS CLI configuration..."
    
    if ! command -v aws &> /dev/null; then
        echo_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    
    if ! aws sts get-caller-identity &> /dev/null; then
        echo_error "AWS CLI is not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    echo_success "AWS CLI is configured"
}

# Create S3 buckets
create_s3_buckets() {
    echo_info "Creating S3 buckets..."
    
    # Create input bucket
    if aws s3 ls "s3://$INPUT_BUCKET" 2>&1 | grep -q 'NoSuchBucket'; then
        echo_info "Creating input bucket: $INPUT_BUCKET"
        aws s3 mb "s3://$INPUT_BUCKET" --region $REGION
        echo_success "Created input bucket: $INPUT_BUCKET"
    else
        echo_info "Input bucket already exists: $INPUT_BUCKET"
    fi
    
    # Create output bucket
    if aws s3 ls "s3://$OUTPUT_BUCKET" 2>&1 | grep -q 'NoSuchBucket'; then
        echo_info "Creating output bucket: $OUTPUT_BUCKET"
        aws s3 mb "s3://$OUTPUT_BUCKET" --region $REGION
        echo_success "Created output bucket: $OUTPUT_BUCKET"
    else
        echo_info "Output bucket already exists: $OUTPUT_BUCKET"
    fi
    
    # Enable versioning on both buckets
    echo_info "Enabling versioning on S3 buckets..."
    aws s3api put-bucket-versioning --bucket $INPUT_BUCKET --versioning-configuration Status=Enabled
    aws s3api put-bucket-versioning --bucket $OUTPUT_BUCKET --versioning-configuration Status=Enabled
    
    echo_success "S3 buckets configured successfully"
}

# Get the latest Ubuntu 22.04 AMI ID
get_ami_id() {
    echo_info "Getting latest Ubuntu 22.04 AMI ID..."
    AMI_ID=$(aws ec2 describe-images \
        --owners 099720109477 \
        --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*" \
        --query 'Images|sort_by(@,&CreationDate)|[-1]|ImageId' \
        --output text \
        --region $REGION)
    
    if [ "$AMI_ID" = "None" ] || [ -z "$AMI_ID" ]; then
        echo_error "Could not find Ubuntu 22.04 AMI ID"
        exit 1
    fi
    
    echo_success "Found AMI ID: $AMI_ID"
}

# Create security group
create_security_group() {
    echo_info "Creating security group..."
    
    # Check if security group already exists
    SG_ID=$(aws ec2 describe-security-groups \
        --filters "Name=group-name,Values=langflix-sg" \
        --query 'SecurityGroups[0].GroupId' \
        --output text \
        --region $REGION)
    
    if [ "$SG_ID" = "None" ] || [ -z "$SG_ID" ]; then
        # Create security group
        SG_ID=$(aws ec2 create-security-group \
            --group-name langflix-sg \
            --description "LangFlix EC2 Security Group" \
            --query 'GroupId' \
            --output text \
            --region $REGION)
        
        # Add SSH rule (you'll need to modify this with your IP)
        echo_warning "Adding SSH rule for 0.0.0.0/0 - please modify this for your security needs"
        aws ec2 authorize-security-group-ingress \
            --group-id $SG_ID \
            --protocol tcp \
            --port 22 \
            --cidr 0.0.0.0/0 \
            --region $REGION
        
        echo_success "Created security group: $SG_ID"
    else
        echo_info "Security group already exists: $SG_ID"
    fi
}

# Create key pair if needed
create_key_pair() {
    if [ -n "$KEY_PAIR_NAME" ]; then
        echo_info "Checking key pair: $KEY_PAIR_NAME"
        
        if ! aws ec2 describe-key-pairs --key-names $KEY_PAIR_NAME --region $REGION &> /dev/null; then
            echo_info "Creating key pair: $KEY_PAIR_NAME"
            aws ec2 create-key-pair \
                --key-name $KEY_PAIR_NAME \
                --query 'KeyMaterial' \
                --output text \
                --region $REGION > "${KEY_PAIR_NAME}.pem"
            
            chmod 600 "${KEY_PAIR_NAME}.pem"
            echo_success "Created key pair: $KEY_PAIR_NAME"
            echo_warning "Key pair file saved as: ${KEY_PAIR_NAME}.pem"
        else
            echo_info "Key pair already exists: $KEY_PAIR_NAME"
        fi
    else
        echo_warning "No key pair name specified. You'll need to create one manually."
    fi
}

# Launch EC2 instance
launch_ec2_instance() {
    if [ -z "$KEY_PAIR_NAME" ]; then
        echo_error "Key pair name is required to launch EC2 instance"
        echo_info "Set KEY_PAIR_NAME environment variable or create one manually"
        exit 1
    fi
    
    echo_info "Launching EC2 instance..."
    
    INSTANCE_ID=$(aws ec2 run-instances \
        --image-id $AMI_ID \
        --count 1 \
        --instance-type $INSTANCE_TYPE \
        --key-name $KEY_PAIR_NAME \
        --security-group-ids $SG_ID \
        --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":50,"VolumeType":"gp3"}}]' \
        --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=langflix-server},{Key=Project,Value=langflix}]' \
        --query 'Instances[0].InstanceId' \
        --output text \
        --region $REGION)
    
    echo_success "Launching instance: $INSTANCE_ID"
    
    # Wait for instance to be running
    echo_info "Waiting for instance to be running..."
    aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $REGION
    
    # Get public IP
    PUBLIC_IP=$(aws ec2 describe-instances \
        --instance-ids $INSTANCE_ID \
        --query 'Reservations[0].Instances[0].PublicIpAddress' \
        --output text \
        --region $REGION)
    
    echo_success "Instance is running!"
    echo_info "Instance ID: $INSTANCE_ID"
    echo_info "Public IP: $PUBLIC_IP"
}

# Create EBS volume for data
create_ebs_volume() {
    echo_info "Creating EBS volume for data storage..."
    
    VOLUME_ID=$(aws ec2 create-volume \
        --size 500 \
        --volume-type gp3 \
        --availability-zone ${REGION}a \
        --tag-specifications 'ResourceType=volume,Tags=[{Key=Name,Value=langflix-data},{Key=Project,Value=langflix}]' \
        --query 'VolumeId' \
        --output text \
        --region $REGION)
    
    echo_success "Created EBS volume: $VOLUME_ID"
    echo_warning "You'll need to attach this volume manually to your EC2 instance"
    echo_warning "Volume ID: $VOLUME_ID"
}

# Main execution
main() {
    echo_info "Starting LangFlix AWS resource setup..."
    echo_info "Region: $REGION"
    echo_info "Input bucket: $INPUT_BUCKET"
    echo_info "Output bucket: $OUTPUT_BUCKET"
    echo_info "Instance type: $INSTANCE_TYPE"
    
    check_aws_cli
    create_s3_buckets
    get_ami_id
    create_security_group
    create_key_pair
    
    if [ "$1" = "--with-instance" ]; then
        launch_ec2_instance
        create_ebs_volume
        
        echo_success "Setup complete!"
        echo_info "Next steps:"
        echo_info "1. SSH into your instance: ssh -i ${KEY_PAIR_NAME}.pem ubuntu@$PUBLIC_IP"
        echo_info "2. Run the EC2 setup script: sudo ./ec2-setup.sh"
        echo_info "3. Configure your environment variables and config files"
    else
        echo_success "AWS resources created!"
        echo_info "To launch an EC2 instance, run: $0 --with-instance"
        echo_info "Available S3 buckets:"
        echo_info "  - Input: s3://$INPUT_BUCKET"
        echo_info "  - Output: s3://$OUTPUT_BUCKET"
    fi
}

# Run main function with all arguments
main "$@"
