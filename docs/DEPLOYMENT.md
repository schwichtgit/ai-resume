# Deployment Guide

## Architecture Overview

The AI Resume stack consists of three runtime services plus a one-shot ingest pipeline:

| Service              | Base Image                        | Port  | Protocol | Lifecycle  |
| -------------------- | --------------------------------- | ----- | -------- | ---------- |
| ai-resume-frontend   | Alpine 3.23 (OpenResty/nginx)     | 8080  | HTTP     | Long-lived |
| ai-resume-api        | Python 3.12 slim-bookworm         | 3000  | HTTP     | Long-lived |
| ai-resume-memvid     | Debian trixie-slim (Rust binary)  | 50051 | gRPC     | Long-lived |
| ai-resume-ingest     | Python 3.12                       | --    | --       | One-shot   |

Traffic flow: reverse proxy -> frontend (8080) -> api (3000) -> memvid (50051 gRPC)

The ingest service runs once to build the `.mv2` vector database file from
`master_resume.md`, then exits (`restart: "no"`).

## Container Image Architecture Support

All service images build and run on both **amd64** and **arm64** architectures.

| Service        | amd64 | arm64 | Notes                                       |
| -------------- | ----- | ----- | ------------------------------------------- |
| frontend       | Yes   | Yes   | Alpine + OpenResty available on both arches |
| api-service    | Yes   | Yes   | Python slim-bookworm multi-arch base        |
| memvid-service | Yes   | Yes   | Rust cross-compiles via `--platform` flag   |

The memvid-service Dockerfile uses `ARG TARGETARCH` for platform-aware builds.
The frontend and api-service use base images that natively support both architectures.

## Building Multi-Architecture Images

### With Podman (recommended)

Build multi-arch manifests for all services:

```bash
# Create manifest and build for both architectures
for svc in frontend api-service memvid-service; do
  podman manifest create localhost/ai-resume-${svc}:latest
  podman build --platform linux/amd64 --manifest localhost/ai-resume-${svc}:latest ${svc}/
  podman build --platform linux/arm64 --manifest localhost/ai-resume-${svc}:latest ${svc}/
done
```

Inspect manifest to verify architectures:

```bash
podman manifest inspect localhost/ai-resume-frontend:latest
```

### With Docker Buildx

```bash
docker buildx create --use --name multiarch

for svc in frontend api-service memvid-service; do
  docker buildx build \
    --platform linux/amd64,linux/arm64 \
    -t ai-resume-${svc}:latest \
    --load \
    ${svc}/
done
```

### Single-Architecture Build

For local development or same-arch deployments:

```bash
# Builds for the host architecture only
docker build -t ai-resume-frontend:latest frontend/
docker build -t ai-resume-api:latest api-service/
docker build -t ai-resume-memvid:latest memvid-service/
```

## Memory Requirements

Per the project constitution, each service must run within **<200MB** of memory.
The `deployment/compose.yaml` enforces this with deploy resource limits:

```yaml
deploy:
  resources:
    limits:
      memory: 200M
```

All three services are configured with this 200MB hard limit, ensuring the full
stack fits within 600MB total -- well within a 4GB ARM64 edge device.

Typical observed memory usage:

| Service          | Idle   | Under Load | Limit |
| ---------------- | ------ | ---------- | ----- |
| frontend         | ~15MB  | ~30MB      | 200M  |
| api-service      | ~60MB  | ~120MB     | 200M  |
| memvid-service   | ~20MB  | ~80MB      | 200M  |

## ARM64 / Edge Deployment

The stack is designed to run on ARM64 edge devices (Raspberry Pi 4/5, NanoPi,
ODROID, or any ARM64 SBC with 4GB+ RAM).

### Prerequisites

- ARM64 Linux host (aarch64)
- Podman 4.x+ or Docker 24.x+ with Compose v2
- 4GB RAM minimum
- Network connectivity for OpenRouter API calls (LLM inference)

### Quick Start

1. Prepare the host directory structure:

```bash
sudo mkdir -p /opt/ai-resume/data/.memvid
# Copy your trained .mv2 file
sudo cp resume.mv2 /opt/ai-resume/data/.memvid/
```

1. Configure environment:

```bash
cd deployment/
cp .env.example .env
# Edit .env -- at minimum set OPENROUTER_API_KEY
```

1. Create the network:

```bash
podman network create yellow-net \
  --subnet 192.168.100.0/24 \
  --gateway 192.168.100.1
```

1. Start the stack:

```bash
cd deployment/
podman compose up -d
```

1. Verify all services are healthy:

```bash
podman compose ps
# All services should show "healthy" status
```

The frontend is accessible at `http://<host-ip>:8080`.

### Deploying with Docker Compose

```bash
cd deployment/
docker compose up -d
docker compose ps
```

### Security Hardening

The compose configuration includes several hardening measures already applied:

- `read_only: true` -- read-only root filesystem on all containers
- `no-new-privileges:true` -- prevents privilege escalation
- Non-root users in all Dockerfiles (nginx, appuser, memvid)
- tmpfs mounts for writable paths with size limits
- Health checks on all services with dependency ordering

### Updating Images

```bash
cd deployment/

# Pull or rebuild images
podman compose pull  # if using a registry
# OR rebuild locally:
# podman build -t localhost/ai-resume-frontend:latest ../frontend/
# podman build -t localhost/ai-resume-api:latest ../api-service/
# podman build -t localhost/ai-resume-memvid:latest ../memvid-service/

# Rolling restart
podman compose up -d
```

### Troubleshooting

Check service logs:

```bash
podman compose logs ai-resume-memvid
podman compose logs ai-resume-api
podman compose logs ai-resume-frontend
```

Verify gRPC connectivity from api to memvid:

```bash
podman exec ai-resume-api python -c "
import grpc
ch = grpc.insecure_channel('ai-resume-memvid:50051')
grpc.channel_ready_future(ch).result(timeout=5)
print('gRPC channel ready')
"
```

Check memory usage against limits:

```bash
podman stats --no-stream
```
