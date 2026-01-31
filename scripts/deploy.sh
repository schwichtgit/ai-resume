#!/bin/bash
# AI Resume - Production Deployment Script
# Builds multi-arch containers and deploys to edge server
#
# Usage:
#   ./scripts/deploy.sh <server_user@host> [version]
#
# Example:
#   ./scripts/deploy.sh user@nanopi-r6s latest
#   ./scripts/deploy.sh user@edge.example.com v1.0.0

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

log_section() {
    echo -e "${BLUE}>>> $1${NC}"
}

# Validate arguments
if [ $# -lt 1 ]; then
    log_error "Usage: $0 <server_user@host> [version]"
fi

SERVER="$1"
VERSION="${2:-latest}"

log_section "AI Resume Deployment Pipeline"
echo "Target: $SERVER"
echo "Version: $VERSION"
echo ""

# Step 1: Build multi-arch containers
log_section "Step 1: Building multi-arch containers"
if ! ./scripts/build-all.sh "$VERSION"; then
    log_error "Container build failed"
fi

# Step 2: Save container images
log_section "Step 2: Saving container images as tarballs"
log_info "Saving frontend container..."
podman save --multi-image-archive localhost/ai-resume-frontend:"${VERSION}" -o "ai-resume-frontend-${VERSION}.tar" || log_error "Failed to save frontend"

log_info "Saving memvid service..."
podman save --multi-image-archive localhost/ai-resume-memvid:"${VERSION}" -o "ai-resume-memvid-${VERSION}.tar" || log_error "Failed to save memvid"

log_info "Saving API service..."
podman save --multi-image-archive localhost/ai-resume-api:"${VERSION}" -o "ai-resume-api-${VERSION}.tar" || log_error "Failed to save API"

# Step 3: Check for memvid data file
log_section "Step 3: Verifying memvid data file"
MEMVID_FILE=$(find data/.memvid -name "*.mv2" -type f | head -1)
if [ -z "$MEMVID_FILE" ]; then
    log_warn "No .mv2 file found in data/.memvid/"
    log_warn "You must have trained memvid locally first: ./scripts/train-memvid.sh"
    log_error "Cannot proceed without memvid file"
fi
log_info "Found memvid file: $MEMVID_FILE"

# Step 4: Transfer files to server
log_section "Step 4: Transferring files to server"
log_info "Creating remote directories..."
ssh "$SERVER" "mkdir -p /opt/ai-resume/data/memvid /opt/ai-resume/deployment" || log_error "Failed to create remote directories"

log_info "Uploading container images (~200MB)..."
scp ai-resume-frontend-"${VERSION}".tar ai-resume-memvid-"${VERSION}".tar ai-resume-api-"${VERSION}".tar "$SERVER:/tmp/" || log_error "Failed to transfer containers"

log_info "Uploading memvid data file..."
scp "$MEMVID_FILE" "$SERVER:/opt/ai-resume/data/memvid/" || log_error "Failed to transfer memvid file"

log_info "Uploading compose.yaml and .env.example..."
scp deployment/compose.yaml "$SERVER:/opt/ai-resume/deployment/" || log_error "Failed to transfer compose.yaml"
scp deployment/.env.example "$SERVER:/opt/ai-resume/deployment/.env" || log_error "Failed to transfer .env template"

# Step 5: Load and deploy on remote server
log_section "Step 5: Loading containers and starting services on remote server"
ssh "$SERVER" << 'REMOTE_SCRIPT'
    set -euo pipefail

    echo "Loading container images..."
    podman load -i /tmp/ai-resume-frontend-*.tar
    podman load -i /tmp/ai-resume-memvid-*.tar
    podman load -i /tmp/ai-resume-api-*.tar

    echo "Cleaning up transferred tarballs..."
    rm -f /tmp/ai-resume-*.tar

    echo "Starting services..."
    cd /opt/ai-resume/deployment

    # Check if .env is configured
    if grep -q "sk-or-v1-your-key-here" .env; then
        echo ""
        echo "⚠️  WARNING: OPENROUTER_API_KEY not configured in .env"
        echo "Please edit /opt/ai-resume/deployment/.env and set your API key"
        echo ""
    fi

    podman-compose up -d

    echo "Waiting for services to be healthy..."
    sleep 5

    # Health checks
    echo "Checking frontend health..."
    podman exec ai-resume-frontend wget --spider http://localhost:8080/health || echo "⚠️  Frontend health check pending..."

    echo "Checking API health..."
    podman exec ai-resume-api wget --spider http://localhost:3000/api/v1/health || echo "⚠️  API health check pending..."
REMOTE_SCRIPT

if [ $? -eq 0 ]; then
    log_section "✓ Deployment successful!"
    echo ""
    echo "Next steps:"
    echo "  1. SSH into server: ssh $SERVER"
    echo "  2. Configure .env: nano /opt/ai-resume/deployment/.env"
    echo "  3. Restart services: cd /opt/ai-resume/deployment && podman-compose restart"
    echo ""
    echo "View logs:"
    echo "  ssh $SERVER 'cd /opt/ai-resume/deployment && podman-compose logs -f'"
    echo ""
else
    log_error "Deployment failed - check remote server logs"
fi
