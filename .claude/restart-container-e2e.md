# Restart Prompt: Container E2E Testing

## Context

Phase 7 greenfield implementation is COMPLETE. All 34 greenfield features implemented
across 12 batches. All 124/124 features in `feature_list.json` now have `passes: true`.

**Quality gates verified:**

- Frontend: 40 tests pass, lint clean, TS clean
- API service: 434 tests pass (5 xfailed), 91% coverage, ruff clean
- Ingest: 90 tests pass, 92% coverage
- Memvid service: cargo check/clippy/test pass

**Branch:** `chore/specforge-migration`

## What's Next: Container E2E Testing

Containers have NEVER been built or tested from the current code. All prior testing
was unit tests, mocked integration tests, and structural checks (file existence).

### Pre-flight Status (verified clean)

- Ports 50051, 3000, 8080: FREE
- No conflicting local processes
- No stale podman containers
- `yellow-net` network exists with correct subnet (192.168.100.0/24)
- `data/.memvid/resume.mv2` exists (317KB)
- `deployment/.env` exists with OPENROUTER_API_KEY

### Steps to Execute

1. **Build native-arch images (arm64)** for local testing:

```bash
cd /Users/frank/projects/MY/AI-RESUME/ai-resume

# Build each image for native arch only (fast, no cross-compile)
podman build -t localhost/ai-resume-memvid:latest -f memvid-service/Dockerfile memvid-service/
podman build -t localhost/ai-resume-api:latest -f api-service/Dockerfile api-service/
podman build -t localhost/ai-resume-frontend:latest -f frontend/Dockerfile frontend/
podman build -t localhost/ai-resume-ingest:latest -f ingest/Dockerfile ingest/
```

1. **Save tarballs for production deployment:**

```bash
mkdir -p dist/
podman save localhost/ai-resume-memvid:latest -o dist/ai-resume-memvid.tar
podman save localhost/ai-resume-api:latest -o dist/ai-resume-api.tar
podman save localhost/ai-resume-frontend:latest -o dist/ai-resume-frontend.tar
podman save localhost/ai-resume-ingest:latest -o dist/ai-resume-ingest.tar
```

For multi-arch production tarballs (slow, cross-compiles):

```bash
./scripts/build-all.sh latest
# Then save manifests:
podman save --multi-image-archive localhost/ai-resume-memvid:latest -o dist/ai-resume-memvid-multiarch.tar
# etc.
```

1. **Start the compose stack:**

```bash
cd deployment/
podman-compose up -d
```

Wait for healthchecks:

```bash
podman-compose ps  # Check health status
```

1. **Test E2E through container stack:**

```bash
# Health checks
curl http://localhost:8080/health       # Frontend (nginx)
curl http://localhost:3000/api/v1/health # API direct
curl http://localhost:8080/api/v1/health # API via frontend proxy

# Profile
curl http://localhost:8080/api/v1/profile | python3 -m json.tool | head -20

# Chat (real E2E through all services)
curl -X POST http://localhost:8080/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What experience does the candidate have?", "session_id": null}'
```

1. **Cleanup after testing:**

```bash
cd deployment/
podman-compose down
```

### Key Files

- `scripts/build-all.sh` -- multi-arch build script (builds manifests, not single images)
- `deployment/compose.yaml` -- compose file with all 4 services
- `deployment/.env` -- environment variables (has OPENROUTER_API_KEY)
- `scripts/test-containers.sh` -- smoke test script (structural checks only currently)

### Known Issues to Watch For

- Ingest Dockerfile CMD is `python ingest.py` which looks for `master_resume.md` by default
  - The test data is `example_resume.md` -- may need command override
  - But `resume.mv2` already exists from previous ingest, so skip ingest container for E2E test
- Memvid healthcheck is `/healthcheck` binary -- verify it exists in the image
- API healthcheck is `/healthcheck` binary -- verify it exists in the image
- Frontend healthcheck uses `wget --spider http://localhost:8080/health`
- compose depends_on chain: memvid healthy -> api starts -> api healthy -> frontend starts
- `read_only: true` on all containers -- if a service tries to write somewhere unexpected, it fails

### After E2E Testing

If containers work:

1. Build multi-arch images for production: `./scripts/build-all.sh v1.0.0`
2. Save production tarballs
3. Commit all Phase 7 work with a single squashed commit
4. Create PR to main
