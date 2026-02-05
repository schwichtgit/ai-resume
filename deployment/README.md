# Deployment Guide

This directory contains the Podman Compose configuration for deploying the AI Resume application with network isolation.

## Quick Reference

```bash
# Start all services
podman-compose up -d

# View logs
podman-compose logs -f [ai-resume-frontend|ai-resume-api|ai-resume-memvid]

# Stop services
podman-compose down

# Restart single service
podman-compose restart ai-resume-api

# Update .mv2 file
scp data/.memvid/resume.mv2 user@edge:/opt/ai-resume/data/.memvid/
ssh user@edge "cd /opt/ai-resume/deployment && podman-compose restart ai-resume-memvid ai-resume-api"
```

## Architecture Overview

This deployment uses an isolated Podman network (`yellow-net`) with static IP assignments. While the default bridge driver provides automatic DNS resolution via Podman's built-in DNS server, this project uses static IPs to demonstrate compatibility with network drivers like `macvlan` (used when connecting to parent VLAN devices) that don't provide DNS services. This approach ensures the configuration works across different network driver scenarios where the host OS would need to provide DHCP/DNS services.

**Network Topology:** See [ARCHITECTURE.md](../docs/ARCHITECTURE.md) for full details.

```text
Host nginx (TLS) → ai-resume-frontend (.10:8080) → ai-resume-api (.11:3000) → ai-resume-memvid (.12:50051)
                                Yellow Zone: 192.168.100.0/24
```

- **ai-resume-frontend**: nginx serving SPA, routes `/api/*` to ai-resume-api
- **ai-resume-api**: FastAPI backend, gRPC client
- **ai-resume-memvid**: memvid gRPC server
- **yellow-net**: Isolated Podman network with static IPs (bridge driver)

## Prerequisites

### 1. Create Yellow Zone Network (one-time)

```bash
podman network create yellow-net \
  --subnet 192.168.100.0/24 \
  --gateway 192.168.100.1
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

### 4. Deploy .mv2 File

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

### 6. Configure Host nginx

For TLS termination and routing to yellow zone. See [docs/SETUP.md](../docs/SETUP.md) for full nginx configuration.

```nginx
# /etc/nginx/sites-available/frank-resume.conf
server {
    listen 443 ssl http2;
    server_name frank-resume.domain.com;

    ssl_certificate     /path/to/fullchain.pem;
    ssl_certificate_key /path/to/privkey.pem;

    location / {
        proxy_pass http://192.168.100.10:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE support for streaming
        proxy_set_header Connection '';
        proxy_buffering off;
    }
}
```

## Deployment

**Start all services:**
```bash
cd deployment
podman-compose up -d
```

**Verify container IPs:**
```bash
podman network inspect yellow-net | grep -A2 '"Name"'
```

Expected:
- ai-resume-frontend: 192.168.100.10
- ai-resume-api: 192.168.100.11
- ai-resume-memvid: 192.168.100.12

**Test endpoints (requires route to yellow-net):**
```bash
# Frontend health
curl http://192.168.100.10:8080/health

# API health (via frontend routing)
curl http://192.168.100.10:8080/api/v1/health

# Chat endpoint
curl -X POST http://192.168.100.10:8080/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What experience do they have?", "session_id": "test-123", "stream": false}'
```

## Production Deployment (Edge Server)

1. **Build locally:**
   ```bash
   ./scripts/build-all.sh latest
   ```

2. **Save and transfer images:**
   ```bash
   podman save localhost/ai-resume-frontend:latest -o frontend.tar
   podman save localhost/ai-resume-api:latest -o api.tar
   podman save localhost/ai-resume-rust:latest -o rust.tar

   scp *.tar user@edge:/tmp/
   scp data/.memvid/resume.mv2 user@edge:/opt/ai-resume/data/.memvid/
   scp deployment/{compose.yaml,.env} user@edge:/opt/ai-resume/deployment/
   ```

3. **On edge server:**
   ```bash
   # Create network (one-time)
   podman network create yellow-net --subnet 192.168.100.0/24

   # Load images
   cd /tmp
   podman load -i frontend.tar
   podman load -i api.tar
   podman load -i rust.tar

   # Deploy
   cd /opt/ai-resume/deployment
   podman-compose up -d
   ```

4. **Configure host nginx and firewall** (see [docs/SETUP.md](../docs/SETUP.md))

## Troubleshooting

**Host nginx can't reach frontend:**
```bash
# Check routing
ip route | grep 192.168.100

# Add route if missing
sudo ip route add 192.168.100.0/24 dev podman1
```

**Containers not getting static IPs:**
```bash
# Verify network is external
podman network ls | grep yellow-net

# Check compose configuration
grep -A2 "yellow-net:" compose.yaml
```

**ai-resume-api can't reach ai-resume-memvid:**
```bash
# Test connectivity
podman exec ai-resume-api ping 192.168.100.12
podman exec ai-resume-api nc -zv 192.168.100.12 50051
```

**Memvid service failing to load .mv2:**
```bash
# Check volume mount and permissions
podman inspect ai-resume-memvid | jq '.[0].Mounts'
ls -la /opt/ai-resume/data/.memvid/resume.mv2
```
