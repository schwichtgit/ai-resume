# Setup & Deployment Guide

Complete guide for local development setup and production deployment.

## Prerequisites

### Local Development

- **Node.js** 24.13.0 LTS "Krypton" (for frontend)
- **Rust** 1.84.0 (for memvid-service)
- **Python** 3.12 or 3.13 with `uv` (for api-service)
- **Podman** 5.0+ (for containers, Docker compatible)

**Container Stable Versions:**

- **Node.js** 24-alpine (build)
- **Rust** 1.84 (compilation)
- **Python** 3.12-slim (runtime)
- **nginx** 1.28-alpine (frontend server)

### Edge Server Deployment

- **Podman** (for running containers)
- SSH access to target server

---

## Quick Start: Local Development

### One-Command Setup

```bash
./scripts/dev-setup.sh
```

This script will:

1. Check all prerequisites
2. Install npm dependencies
3. Set up Python virtual environment with UV
4. Fetch Rust dependencies
5. Optionally build multi-arch containers

### Manual Setup

**Frontend:**

```bash
npm ci
npm run dev  # Start dev server at http://localhost:8080
```

**Python API Server:**

```bash
cd api-service
uv venv .venv && source .venv/bin/activate
uv sync

# Set environment variables
export OPENROUTER_API_KEY="your-key"
export MEMVID_GRPC_URL="localhost:50051"

# Run with hot reload
uv run uvicorn ai_resume_api.main:app --reload --port 3000
```

**Rust Memvid Service:**

```bash
cd memvid-service
export MEMVID_FILE_PATH="/path/to/your/resume.mv2"
cargo run --release
```

**Local Testing with Compose:**

```bash
# All three services together
cd deployment/
cp .env.example .env
# Edit .env with your API key
podman-compose up -d

# View logs
podman-compose logs -f

# Stop
podman-compose down
```

---

## Building Containers

### Build Prerequisites

1. **Train memvid first:**

   ```bash
   ./scripts/train-memvid.sh
   ```

   This creates `data/.memvid/resume.mv2`

2. **Build frontend (if needed):**

   ```bash
   npm run build
   ```

### Build Multi-Architecture Containers

```bash
./scripts/build-all.sh latest
```

This builds for **both amd64 and arm64** automatically:

- `ai-resume-frontend:latest`
- `ai-resume-api:latest`
- `ai-resume-memvid:latest`

**View built images:**

```bash
podman manifest inspect localhost/ai-resume-frontend:latest
```

---

## Production Deployment

### Automated Deployment to Edge Server

```bash
./scripts/deploy.sh user@your-server latest
```

This script:

1. Builds multi-arch containers
2. Saves them as tarballs
3. Transfers to remote server (containers + memvid data + config)
4. Loads containers on remote
5. Starts services with `podman-compose`

**Example:**

```bash
./scripts/deploy.sh frank@nanopi-r6s latest
```

### Manual Deployment (Step by Step)

#### Step 1: Prepare on Development Machine

```bash
# Build multi-arch containers
./scripts/build-all.sh latest

# Verify memvid file exists
ls data/.memvid/resume.mv2

# Save containers as tarballs
podman save --multi-image-archive localhost/ai-resume-frontend:latest -o ai-resume-frontend-latest.tar
podman save --multi-image-archive localhost/ai-resume-api:latest -o ai-resume-api-latest.tar
podman save --multi-image-archive localhost/ai-resume-memvid:latest -o ai-resume-memvid-latest.tar
```

#### Step 2: Transfer to Server

```bash
# Create directories
ssh user@server "mkdir -p /opt/ai-resume/data/memvid /opt/ai-resume/deployment"

# Transfer containers (total ~200MB)
scp ai-resume-frontend-latest.tar ai-resume-api-latest.tar ai-resume-memvid-latest.tar user@server:/tmp/

# Transfer memvid data
scp data/.memvid/resume.mv2 user@server:/opt/ai-resume/data/memvid/

# Transfer configuration
scp deployment/compose.yaml deployment/.env.example user@server:/opt/ai-resume/deployment/
```

#### Step 3: Deploy on Remote Server

```bash
ssh user@server

cd /opt/ai-resume

# Load container images
podman load -i /tmp/ai-resume-frontend-latest.tar
podman load -i /tmp/ai-resume-api-latest.tar
podman load -i /tmp/ai-resume-memvid-latest.tar

# Clean up tarballs
rm /tmp/ai-resume-*.tar

# Configure secrets
cp deployment/.env.example deployment/.env
# IMPORTANT: Edit .env and add your OPENROUTER_API_KEY
nano deployment/.env

# Start services
cd deployment/
podman-compose up -d

# Check status
podman-compose logs -f
```

#### Step 4: Verify Deployment

```bash
# Health checks
curl http://localhost:8080/health        # Frontend
curl http://localhost:3000/api/v1/health # API
podman exec ai-resume-memvid curl http://localhost:9090/metrics # Memvid
```

---

## Configuration

### Environment Variables (`.env`)

See `deployment/.env.example` for all options:

```bash
# REQUIRED
OPENROUTER_API_KEY=sk-or-v1-your-key

# Site Configuration
SITE_DOMAIN=your-domain.com
MEMVID_FILENAME=resume.mv2
MEMVID_DATA_PATH=/opt/ai-resume/data/memvid

# LLM Model
LLM_MODEL=nvidia/nemotron-nano-2407-instruct

# Optional: Container Registry
REGISTRY=localhost
VERSION=latest

# API Tuning
SESSION_TTL=1800
RATE_LIMIT=10
LOG_LEVEL=INFO
```

### Resume Data Configuration (Data-Driven Architecture)

All profile data comes from a single markdown file processed by the ingest pipeline.

**Create your resume (see `data/example_resume.md` for template):**

```bash
# Copy example as starting point
cp data/example_resume.md data/your_resume.md

# Edit with your information
nano data/your_resume.md
```

**Key sections in the markdown file:**

- **YAML Frontmatter** - name, title, email, linkedin, status, suggested_questions, system_prompt, tags
- **Summary** - Professional overview
- **FAQ** - Pre-indexed question/answer pairs (mirrors suggested_questions)
- **Professional Experience** - Jobs with AI Context (situation, approach, technical work, lessons)
- **Skills Assessment** - Strong/Moderate/Gaps categorization
- **Fit Assessment Examples** - Pre-analyzed job fit scenarios

**Schema documentation:** See `docs/MASTER_DOCUMENT_SCHEMA.md`

---

## Updating Resume Data

After updating your markdown resume:

```bash
# 1. Run ingest locally
cd ingest/
source .venv/bin/activate
python ingest.py --input ../data/your_resume.md --output ../data/.memvid/resume.mv2

# 2. Transfer to server (only the .mv2 file needed!)
scp data/.memvid/resume.mv2 user@server:/opt/ai-resume/data/memvid/

# 3. Restart services to pick up new data
ssh user@server "cd /opt/ai-resume/deployment && podman-compose restart memvid-service api-service"
```

**Note:** Profile metadata is stored INSIDE the .mv2 file - no separate config files needed!

---

## Troubleshooting

### Frontend Container Won't Start

```bash
podman logs ai-resume-frontend
# Check: nginx.conf, port 8080 in use, volume mounts
```

### API Server Can't Connect to Memvid

```bash
podman logs ai-resume-api
# Check: MEMVID_GRPC_URL, network connectivity
podman exec ai-resume-api ping memvid-service
```

### OpenRouter API Errors

```bash
podman exec ai-resume-api env | grep OPENROUTER_API_KEY
# Verify: API key is set, not expired, has credits
```

### Container Build Fails

```bash
# If frontend build fails with memory error:
npm run build  # Build locally first
# Then retry: ./scripts/build-all.sh latest
```

### Port Already in Use

```bash
# Find what's using port 8080
lsof -i :8080
# Or use different port in compose.yaml
```

---

## Performance Tuning

### Optimize Memory Usage

```bash
# Reduce SESSION_TTL if running on low-memory hardware
export SESSION_TTL=900  # 15 minutes instead of 30

# Limit concurrent API connections
export RATE_LIMIT=5
```

### Monitor Resources

```bash
podman stats --no-stream
```

### Check Memvid Retrieval Speed

```bash
# Should be <5ms for semantic search
curl -X POST http://localhost:3000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"test","stream":false}' | grep latency
```

---

## Network & Security

### Behind Reverse Proxy

Configure Traefik, Caddy, or nginx to:

- Terminate TLS (port 443)
- Route to `localhost:8080`
- Add security headers

Example Traefik labels (in compose.yaml):

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.ai-resume.rule=Host(`your-domain.com`)"
  - "traefik.http.routers.ai-resume.tls.certresolver=letsencrypt"
```

### Internal Network

The three containers communicate over an isolated bridge network:

- `frontend` → publicly exposed on port 8080
- `api-service` → internal only (port 3000)
- `memvid-service` → internal only (port 50051 gRPC)

This prevents direct access to API and memvid services.

---

## Next Steps

- [PRD.md](./PRD.md) - Product requirements and design decisions
- [DESIGN.md](./DESIGN.md) - Detailed architecture
- [SECURITY.md](./SECURITY.md) - Security hardening
- [DEVELOPMENT.md](./DEVELOPMENT.md) - Contributing guide
