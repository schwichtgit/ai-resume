# Container E2E Cheat Sheet

Quick-reference for building, running, and testing the full containerized stack locally. This is the ultimate acceptance gate for the project.

## Prerequisites

| Requirement | How to verify |
| --- | --- |
| Podman machine running | `podman machine info` (machinestate: Running) |
| yellow-net exists | `podman network ls \| grep yellow-net` |
| Deployment venv | `source deployment/.venv/bin/activate && podman-compose --version` |
| `.env` configured | `cat deployment/.env` (needs OPENROUTER_API_KEY, PROJECT_BASE_DIR) |
| Data dir has resume | `ls data/example_resume.md` (source for ingest) |

## Architecture

```text
Host browser
  |
  v  http://localhost:8080
ai-resume-frontend (OpenResty/Alpine, .10:8080)
  |  /api/* proxied via Lua DNS resolver
  v
ai-resume-api (FastAPI/Python 3.12, .11:3000)
  |  gRPC (protobuf)
  v
ai-resume-memvid (Rust binary, .12:50051)
  |  reads .mv2 file from /data/.memvid/resume.mv2
  v
Volume mount: ${PROJECT_BASE_DIR}/data:/data
```

**Network:** `yellow-net` (192.168.100.0/24, bridge driver, static IPs)

**In production:** Only frontend port 8080 is exposed (behind host nginx for TLS). API and memvid are internal to yellow-net. Locally for testing, compose.yaml also exposes API on :3000 and memvid on :50051 for direct debugging.

## Step-by-Step: Full E2E Test

### 1. Activate deployment venv (provides podman-compose)

```bash
cd /Users/frank/projects/MY/AI-RESUME/ai-resume
source deployment/.venv/bin/activate
```

### 2. Ingest example_resume.md into .mv2

The ingest container does this, but you can also do it locally first to have the .mv2 ready:

```bash
source ingest/.venv/bin/activate
python ingest/ingest.py \
  --input data/example_resume.md \
  --output data/.memvid/resume.mv2 \
  --verify
```

Or use the ingest container (one-shot, runs then exits):

```bash
source deployment/.venv/bin/activate
cd deployment
podman-compose run --rm ai-resume-ingest \
  python ingest.py --input /data/example_resume.md --output /data/.memvid/resume.mv2 --verify
```

**Note:** The ingest container default CMD is `python ingest.py` which looks for `/data/master_resume.md`. For example_resume.md you must override the command or copy/symlink the file.

### 3. Build all container images

```bash
cd /Users/frank/projects/MY/AI-RESUME/ai-resume
bash scripts/build-all.sh latest
```

This builds (multi-arch amd64+arm64):

- `localhost/ai-resume-frontend:latest` (node builder -> OpenResty Alpine)
- `localhost/ai-resume-memvid:latest` (rust builder -> debian-slim)
- `localhost/ai-resume-api:latest` (uv builder -> python-slim)
- `localhost/ai-resume-ingest:latest` (uv builder -> python-slim + HuggingFace model)

Verify images exist:

```bash
podman images | grep ai-resume
```

### 4. Bring up the stack

```bash
cd /Users/frank/projects/MY/AI-RESUME/ai-resume/deployment
source .venv/bin/activate
podman-compose up -d
```

Watch logs:

```bash
podman-compose logs -f
```

Check all containers running:

```bash
podman ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### 5. Verify health

```bash
# Frontend health (nginx)
curl -s http://localhost:8080/health

# API health (direct, for debugging)
curl -s http://localhost:3000/health | python3 -m json.tool

# API health via frontend proxy (production path)
curl -s http://localhost:8080/api/v1/health | python3 -m json.tool
```

Expected API health response:

```json
{
  "status": "healthy",
  "memvid_connected": true
}
```

### 6. Functional smoke tests

```bash
# Profile endpoint (via frontend proxy -- the production path)
curl -s http://localhost:8080/api/v1/profile | python3 -m json.tool

# Expected: name="Jane Chen", title="VP of Platform Engineering"

# Suggested questions
curl -s http://localhost:8080/api/v1/suggested-questions | python3 -m json.tool

# Chat (non-streaming)
curl -s -X POST http://localhost:8080/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"What programming languages does she know?","stream":false}' \
  | python3 -m json.tool

# Chat (streaming SSE)
curl -N -X POST http://localhost:8080/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Tell me about her security experience","stream":true}'

# Fit assessment (real-time analysis)
curl -s -X POST http://localhost:8080/api/v1/assess-fit \
  -H "Content-Type: application/json" \
  -d '{"job_description":"VP of Platform Engineering at Series B AI startup. Kubernetes, MLOps, FedRAMP."}' \
  | python3 -m json.tool
```

### 7. Content coverage queries (semantic search quality)

These verify all major resume sections are retrievable via real .mv2 search:

```bash
BASE=http://localhost:8080/api/v1

# FAQ coverage
curl -s -X POST $BASE/chat -H "Content-Type: application/json" -d '{"message":"What is her security track record?","stream":false}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'chunks={d.get(\"chunks_retrieved\",0)} len={len(d.get(\"message\",\"\"))}')"

curl -s -X POST $BASE/chat -H "Content-Type: application/json" -d '{"message":"What programming languages does she know?","stream":false}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'chunks={d.get(\"chunks_retrieved\",0)} len={len(d.get(\"message\",\"\"))}')"

curl -s -X POST $BASE/chat -H "Content-Type: application/json" -d '{"message":"Tell me about her AI and ML experience","stream":false}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'chunks={d.get(\"chunks_retrieved\",0)} len={len(d.get(\"message\",\"\"))}')"

curl -s -X POST $BASE/chat -H "Content-Type: application/json" -d '{"message":"What are her biggest failures?","stream":false}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'chunks={d.get(\"chunks_retrieved\",0)} len={len(d.get(\"message\",\"\"))}')"

curl -s -X POST $BASE/chat -H "Content-Type: application/json" -d '{"message":"Would she be good for an early-stage startup?","stream":false}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'chunks={d.get(\"chunks_retrieved\",0)} len={len(d.get(\"message\",\"\"))}')"

# Experience coverage (per company)
curl -s -X POST $BASE/chat -H "Content-Type: application/json" -d '{"message":"Tell me about her work at Acme Corp","stream":false}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'chunks={d.get(\"chunks_retrieved\",0)} len={len(d.get(\"message\",\"\"))}')"

curl -s -X POST $BASE/chat -H "Content-Type: application/json" -d '{"message":"What did she do at DataFlow with data infrastructure?","stream":false}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'chunks={d.get(\"chunks_retrieved\",0)} len={len(d.get(\"message\",\"\"))}')"

curl -s -X POST $BASE/chat -H "Content-Type: application/json" -d '{"message":"Tell me about her early career at TechStart Labs","stream":false}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'chunks={d.get(\"chunks_retrieved\",0)} len={len(d.get(\"message\",\"\"))}')"

# Skills coverage
curl -s -X POST $BASE/chat -H "Content-Type: application/json" -d '{"message":"What is her Kubernetes and cloud infrastructure experience?","stream":false}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'chunks={d.get(\"chunks_retrieved\",0)} len={len(d.get(\"message\",\"\"))}')"

# Gaps (honest limitations)
curl -s -X POST $BASE/chat -H "Content-Type: application/json" -d '{"message":"What are her technical limitations and skill gaps?","stream":false}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'chunks={d.get(\"chunks_retrieved\",0)} len={len(d.get(\"message\",\"\"))}')"
```

**Pass criteria:** Every query returns `chunks > 0` and `len > 0`.

### 8. Tear down

```bash
cd /Users/frank/projects/MY/AI-RESUME/ai-resume/deployment
source .venv/bin/activate
podman-compose down
```

## Compose Environment Variables (.env)

| Variable | Purpose | Default |
| --- | --- | --- |
| `PROJECT_BASE_DIR` | Host path to project root (volume mount) | `/opt/ai-resume` |
| `OPENROUTER_API_KEY` | LLM API key (required unless MOCK_OPENROUTER) | none |
| `MEMVID_FILENAME` | .mv2 filename inside data/.memvid/ | `resume.mv2` |
| `LLM_MODEL` | OpenRouter model ID | `nvidia/nemotron-nano-9b-v2:free` |
| `REGISTRY` | Container image registry prefix | `localhost` |
| `VERSION` | Image tag | `latest` |
| `SESSION_TTL` | Chat session lifetime (seconds) | `1800` |
| `RATE_LIMIT` | Requests per minute per IP | `10` |
| `LOG_LEVEL` | Service log level | `INFO` |
| `API_BACKEND_HOST` | Frontend->API hostname (for macvlan/no-DNS) | `ai-resume-api` |
| `API_BACKEND_PORT` | Frontend->API port | `3000` |
| `MEMVID_GRPC_HOST` | API->memvid hostname | `ai-resume-memvid` |
| `MEMVID_GRPC_PORT` | API->memvid port | `50051` |
| `BIND_ADDRESS` | IPv4/IPv6 bind (auto/0.0.0.0/::) | `auto` |

## Container Details

| Container | Base Image | Port | Healthcheck | Non-root |
| --- | --- | --- | --- | --- |
| ai-resume-frontend | alpine:3.23 + openresty | 8080 | `wget --spider http://localhost:8080/health` | nginx |
| ai-resume-api | python:3.12-slim-bookworm | 3000 | `/healthcheck` (python script, tries IPv6 then IPv4) | appuser (1000) |
| ai-resume-memvid | debian:trixie-slim | 50051 | `/healthcheck` (symlink to binary) | memvid (1000) |
| ai-resume-ingest | python:3.12-slim-bookworm | none | none (one-shot) | appuser (1000) |

## Startup Order (compose depends_on)

```text
ai-resume-memvid  (starts first, healthcheck must pass)
       |
       v
ai-resume-api     (starts after memvid healthy)
       |
       v
ai-resume-frontend (starts after api healthy)
```

`ai-resume-ingest` is independent (one-shot, run manually or via `podman-compose run`).

## Troubleshooting

```bash
# Check container logs
podman-compose logs ai-resume-memvid
podman-compose logs ai-resume-api
podman-compose logs ai-resume-frontend

# Check if .mv2 file is visible inside memvid container
podman exec ai-resume-memvid ls -la /data/.memvid/

# Check if API can reach memvid via gRPC
podman exec ai-resume-api python -c "import grpc; ch=grpc.insecure_channel('ai-resume-memvid:50051'); print('channel created')"

# Check network connectivity
podman exec ai-resume-api ping -c1 192.168.100.12

# Rebuild a single service
podman build -f api-service/Dockerfile -t localhost/ai-resume-api:latest api-service/
podman-compose up -d ai-resume-api

# Nuclear reset
podman-compose down
podman rmi localhost/ai-resume-frontend:latest localhost/ai-resume-api:latest localhost/ai-resume-memvid:latest localhost/ai-resume-ingest:latest
bash scripts/build-all.sh latest
cd deployment && podman-compose up -d
```

## Key File Locations

| File | Purpose |
| --- | --- |
| `deployment/compose.yaml` | Full stack orchestration spec |
| `deployment/.env` | Runtime configuration (git-ignored, contains API key) |
| `deployment/.env.example` | Template for .env |
| `deployment/.venv/` | Python venv with podman-compose |
| `scripts/build-all.sh` | Builds all 4 container images (multi-arch) |
| `scripts/test-containers.sh` | Podman-native smoke test (without compose) |
| `scripts/test-e2e-real.sh` | Real E2E with native processes (not containers) |
| `frontend/Dockerfile` | OpenResty + React SPA |
| `api-service/Dockerfile` | FastAPI + gRPC client |
| `memvid-service/Dockerfile` | Rust gRPC server |
| `ingest/Dockerfile` | Python ingest pipeline + HuggingFace model |
| `data/example_resume.md` | Example resume (Jane Chen) for testing |
| `data/.memvid/resume.mv2` | Generated vector DB file |
