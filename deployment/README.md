# Deployment Configuration

This directory contains the Podman Compose configuration for the Hybrid Rust + Python architecture with yellow zone network isolation.

## Architecture (Pattern B: Frontend as Router)

```text
┌─────────────────────────────────────────────────────────────────────┐
│                         Host (OpenWrt)                              │
│                                                                     │
│  ┌──────────────┐                                                   │
│  │ Host nginx   │  TLS termination only                             │
│  │    (LB)      │  frank-resume.domain.com → 192.168.100.10:8080    │
│  └──────┬───────┘                                                   │
│         │ HTTP (no TLS)                                             │
│         ▼                                                           │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              Yellow Zone: 192.168.100.0/24                   │   │
│  │              Podman Network: yellow-net                      │   │
│  │                                                              │   │
│  │  ┌─────────────────┐                                         │   │
│  │  │ frontend        │ .10:8080  (nginx + SPA)                 │   │
│  │  │ /     → SPA     │                                         │   │
│  │  │ /api/* → ───────┼──────────────────────┐                  │   │
│  │  └─────────────────┘                      │                  │   │
│  │                                           ▼                  │   │
│  │                              ┌─────────────────┐             │   │
│  │                              │ python-api      │ .11:3000    │   │
│  │                              │ (FastAPI)       │             │   │
│  │                              └────────┬────────┘             │   │
│  │                                       │ gRPC                 │   │
│  │                                       ▼                      │   │
│  │                              ┌─────────────────┐             │   │
│  │                              │ rust-memvid     │ .12:50051   │   │
│  │                              │ (gRPC)          │             │   │
│  │                              └─────────────────┘             │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

**Key Design Decisions:**
- No ports exposed on containers; host nginx connects directly to yellow-net
- Frontend handles all URL routing (`/api/*` → python-api)
- Host LB only knows domain → IP mapping, not application routes
- Static IPs enable precise firewall rules

## Prerequisites

### 1. Create Yellow Zone Network (one-time)

```bash
podman network create yellow-net \
  --subnet 192.168.100.0/24 \
  --gateway 192.168.100.1
```

Verify:
```bash
podman network inspect yellow-net
```

### 2. Create Host Directory Structure

```bash
sudo mkdir -p /opt/ai-resume/{data/.memvid,logs/rust,logs/python}
sudo chown -R $USER:$USER /opt/ai-resume
```

### 3. Build Containers

```bash
cd /path/to/ai-resume
./scripts/build-all.sh latest
```

### 4. Ingest and Deploy .mv2 File

```bash
# Ingest locally (on dev machine)
cd ingest
uv run python ingest.py --verify

# Copy to deployment location
cp ../data/.memvid/resume.mv2 /opt/ai-resume/data/.memvid/
```

### 5. Configure Environment

```bash
cd deployment
cp .env.example .env
nano .env  # Add your OPENROUTER_API_KEY
```

### 6. Configure Host nginx LB

Add to your host nginx configuration:

```nginx
# /etc/nginx/sites-available/frank-resume.conf
server {
    listen 443 ssl http2;
    server_name frank-resume.domain.com;

    ssl_certificate     /path/to/fullchain.pem;
    ssl_certificate_key /path/to/privkey.pem;

    location / {
        proxy_pass http://192.168.100.10:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE support for streaming
        proxy_set_header Connection '';
        proxy_buffering off;
        proxy_cache off;
    }
}
```

## Deployment

**Start all services:**
```bash
cd deployment
podman-compose up -d
```

**View logs:**
```bash
podman-compose logs -f
```

**Stop services:**
```bash
podman-compose down
```

**Restart single service:**
```bash
podman-compose restart python-api
```

## Verification

**Check container IPs:**
```bash
podman network inspect yellow-net | grep -A2 '"Name"'
```

Expected:
- frontend: 192.168.100.10
- python-api: 192.168.100.11
- rust-memvid: 192.168.100.12

**Test from host (must have route to yellow-net):**
```bash
# Frontend health
curl http://192.168.100.10:8080/health

# API health (via frontend routing)
curl http://192.168.100.10:8080/api/v1/health
```

**Test chat endpoint:**
```bash
curl -X POST http://192.168.100.10:8080/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What experience do they have with Kubernetes?",
    "session_id": "test-123",
    "stream": false
  }'
```

## Updating .mv2 File

When you update the resume data:

1. **Re-ingest locally:**
   ```bash
   cd ingest
   uv run python ingest.py --verify
   ```

2. **Copy to edge server:**
   ```bash
   scp ../data/.memvid/resume.mv2 \
     user@edge-server:/opt/ai-resume/data/.memvid/
   ```

3. **Restart memvid service:**
   ```bash
   ssh user@edge-server
   cd /opt/ai-resume/deployment
   podman-compose restart rust-memvid python-api
   ```

## Firewall Rules (OpenWrt)

Isolate yellow zone from other networks:

```bash
# Block yellow → other zones
iptables -A FORWARD -s 192.168.100.0/24 -d 192.168.200.0/24 -j DROP
iptables -A FORWARD -s 192.168.100.0/24 -d 192.168.1.0/24 -j DROP

# Allow yellow → internet (for OpenRouter API)
iptables -A FORWARD -s 192.168.100.0/24 -j ACCEPT
```

## Troubleshooting

**Host nginx can't reach frontend:**
```bash
# Check routing to yellow-net
ip route | grep 192.168.100

# Add route if missing
sudo ip route add 192.168.100.0/24 dev podman1
```

**Containers not getting static IPs:**
```bash
# Verify network is external
podman network ls
# Should show: yellow-net  bridge  external

# Check compose uses external network
grep -A2 "yellow-net:" compose.yaml
```

**python-api can't reach rust-memvid:**
```bash
# Test from inside container
podman exec python-api ping 192.168.100.12

# Check gRPC port
podman exec python-api nc -zv 192.168.100.12 50051
```

**Memvid service failing to load .mv2:**
```bash
# Check volume mount
podman inspect rust-memvid | jq '.[0].Mounts'

# Verify file exists and permissions
ls -la /opt/ai-resume/data/.memvid/
```

## Production Deployment (Edge Server)

1. **Build locally (multi-arch):**
   ```bash
   ./scripts/build-all.sh latest
   ```

2. **Save images:**
   ```bash
   podman save localhost/ai-resume-frontend:latest -o frontend.tar
   podman save localhost/ai-resume-rust:latest -o rust.tar
   podman save localhost/ai-resume-python:latest -o python.tar
   ```

3. **Transfer to edge server:**
   ```bash
   scp *.tar user@edge-server:/tmp/
   scp data/.memvid/resume.mv2 user@edge-server:/opt/ai-resume/data/.memvid/
   scp deployment/{compose.yaml,.env} user@edge-server:/opt/ai-resume/deployment/
   ```

4. **On edge server:**
   ```bash
   # Create network (one-time)
   podman network create yellow-net --subnet 192.168.100.0/24 --gateway 192.168.100.1

   # Load images
   podman load -i /tmp/frontend.tar
   podman load -i /tmp/rust.tar
   podman load -i /tmp/python.tar

   # Deploy
   cd /opt/ai-resume/deployment
   podman-compose up -d
   ```

5. **Configure host nginx and firewall** (see sections above)
