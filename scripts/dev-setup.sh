#!/bin/bash
# AI Resume - Developer Setup Script
# One-command setup for local development environment
#
# Prerequisites:
#   - Node.js 18+ (for frontend)
#   - Rust 1.84+ (for api-server-rust)
#   - Python 3.12+ with uv (for api-server-python)
#   - Podman (for containers)
#
# Usage:
#   ./scripts/dev-setup.sh [--skip-containers]

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
}

log_section() {
    echo -e "${BLUE}>>> $1${NC}"
}

check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "$1 is not installed. Please install it first."
    fi
}

# Parse arguments
SKIP_CONTAINERS=false
if [ "${1:-}" == "--skip-containers" ]; then
    SKIP_CONTAINERS=true
fi

log_section "AI Resume - Developer Setup"
echo ""

# Check prerequisites
log_section "Checking prerequisites..."

# Node.js
check_command node
NODE_VER=$(node --version)
log_info "✓ Node.js found: $NODE_VER"
log_info "  (Required: 24.13.0+ LTS)"

# npm
check_command npm
log_info "✓ npm found: $(npm --version)"

# Rust
check_command cargo
RUST_VER=$(cargo --version)
log_info "✓ Rust found: $RUST_VER"
log_info "  (Required: 1.84.0+)"

# UV
check_command uv
log_info "✓ UV found: $(uv --version)"

# Podman
if [ "$SKIP_CONTAINERS" = false ]; then
    check_command podman
    PODMAN_VER=$(podman --version)
    log_info "✓ Podman found: $PODMAN_VER"
    log_info "  (Required: 5.0+)"
fi

echo ""

# Setup frontend
log_section "Setting up frontend..."
if [ ! -d "node_modules" ]; then
    log_info "Installing npm dependencies..."
    npm ci
else
    log_info "npm dependencies already installed"
fi
log_info "✓ Frontend ready"
echo ""

# Setup Python API server
log_section "Setting up Python API server..."
cd api-server-python
if [ ! -d ".venv" ]; then
    log_info "Creating virtual environment..."
    uv venv .venv
    log_info "Installing dependencies..."
    uv sync
else
    log_info "Virtual environment already exists"
    log_info "Syncing dependencies..."
    uv sync
fi
log_info "✓ Python API server ready"
echo ""

# Setup Rust service
cd ../api-server-rust
log_section "Setting up Rust memvid service..."
if [ ! -f "Cargo.lock" ]; then
    log_info "Fetching Rust dependencies (this may take a moment)..."
    cargo fetch
else
    log_info "Rust dependencies already fetched"
fi
log_info "✓ Rust service ready"
echo ""

cd ..

# Optionally build containers
if [ "$SKIP_CONTAINERS" = false ]; then
    log_section "Building multi-arch containers..."
    if ./scripts/build-all.sh latest; then
        log_info "✓ Containers built successfully"
    else
        log_warn "Container build failed - you can build later with: ./scripts/build-all.sh"
    fi
    echo ""
fi

# Train memvid if not exists
log_section "Checking memvid training..."
if [ ! -f "data/.memvid/resume.mv2" ]; then
    log_warn "No .mv2 file found in data/.memvid/"
    log_warn "You can train it with: ./scripts/train-memvid.sh"
    log_warn "This requires memvid CLI installed locally"
else
    log_info "✓ Memvid file found: data/.memvid/resume.mv2"
fi
echo ""

# Summary
log_section "✓ Setup complete!"
echo ""
echo "Next steps:"
echo ""
echo "1. Frontend development:"
echo "   npm run dev"
echo ""
echo "2. Python API server:"
echo "   cd api-server-python"
echo "   source .venv/bin/activate"
echo "   export OPENROUTER_API_KEY=\"your-key\""
echo "   uv run uvicorn app.main:app --reload --port 3000"
echo ""
echo "3. Rust memvid service:"
echo "   cd api-server-rust"
echo "   export MEMVID_FILE_PATH=\"/path/to/your/resume.mv2\""
echo "   cargo run --release"
echo ""
echo "4. Train memvid from resume data:"
echo "   ./scripts/train-memvid.sh"
echo ""
echo "5. Deploy containers to edge server:"
echo "   ./scripts/deploy.sh user@your-server latest"
echo ""
