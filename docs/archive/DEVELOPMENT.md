# Development Guide

Contributor guide for developing and extending AI Resume.

---

## Project Structure

```text
ai-resume/
├── README.md              # Entry point for users
│
├── frontend/              # React SPA (Vite + TypeScript)
│   ├── Dockerfile         # Multi-arch frontend container
│   ├── nginx.conf         # Nginx configuration & routing
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── pages/         # Page-level components
│   │   └── App.tsx        # Root component
│   └── package.json
│
├── api-service/     # FastAPI orchestration service
│   ├── Dockerfile         # Multi-arch API container
│   ├── pyproject.toml     # Python dependencies (UV)
│   ├── app/
│   │   ├── main.py        # FastAPI entrypoint
│   │   ├── config.py      # Environment configuration
│   │   ├── models.py      # Pydantic request/response models
│   │   ├── memvid_client.py    # gRPC client to Rust service
│   │   ├── openrouter_client.py # OpenRouter LLM calls
│   │   ├── session_store.py     # In-memory session management
│   │   └── rate_limiter.py      # Rate limiting middleware
│   └── tests/
│
├── memvid-service/       # Memvid retrieval service
│   ├── Dockerfile         # Multi-arch Rust container
│   ├── Cargo.toml         # Rust dependencies
│   ├── src/
│   │   ├── main.rs        # gRPC server & memvid loading
│   │   ├── models.rs      # Data structures
│   │   └── grpc/          # Generated protobuf code
│   └── proto/
│       └── memvid.proto   # gRPC service definition
│
├── data/                  # Resume data & trained memory
│   ├── profile.example.toml    # Configuration template
│   ├── master_resume.md        # Content source
│   └── .memvid/
│       └── resume.mv2          # Trained memory file
│
├── deployment/            # Production orchestration
│   ├── compose.yaml       # Podman Compose configuration
│   ├── .env.example       # Environment template
│   └── README.md          # Deployment instructions
│
├── scripts/               # Automation
│   ├── build-all.sh       # Build multi-arch containers
│   ├── train-memvid.sh    # Train memvid from resume
│   ├── deploy.sh          # Deploy to edge server
│   └── dev-setup.sh       # Local dev environment setup
│
└── docs/                  # Documentation
    ├── PRD.md             # Product requirements
    ├── ARCHITECTURE.md          # Architecture & design
    ├── SECURITY.md        # Security hardening
    ├── SETUP.md           # Setup & deployment
    ├── DEVELOPMENT.md     # This file
    └── TODO.md            # Development roadmap
```

---

## Development Workflows

### 1. Frontend Development

```bash
npm run dev
# Starts Vite dev server with hot reload at http://localhost:8080
```

**Key files:**

- `src/components/` - Reusable UI components
- `src/pages/Index.tsx` - Main page (sections)
- `src/lib/api-client.ts` - API service layer
- `src/hooks/useStreamingChat.ts` - SSE streaming hook

**Common tasks:**

- Add new section: Create component in `src/components/`, add to pages/Index.tsx
- Update theme: Edit `tailwind.config.ts`, `src/index.css`
- Add API integration: Use `lib/api-client.ts`

### 2. Python API Server Development

```bash
cd api-service

# Create/activate virtual environment
uv venv .venv && source .venv/bin/activate

# Install dependencies
uv sync

# Run with hot reload
export OPENROUTER_API_KEY="your-key"
export MEMVID_GRPC_URL="localhost:50051"
uv run uvicorn app.main:app --reload --port 3000

# Run tests
uv run pytest

# Type checking
uv run mypy app/

# Code formatting
uv run black app/
uv run isort app/
uv run ruff check app/
```

**Key files:**

- `app/main.py` - FastAPI routes
- `app/config.py` - Environment configuration
- `app/openrouter_client.py` - LLM integration
- `app/memvid_client.py` - gRPC client to Rust service
- `app/session_store.py` - Session management
- `app/rate_limiter.py` - Rate limiting

### 3. Rust Memvid Service Development

```bash
cd memvid-service

# Build
cargo build --release

# Run
export MEMVID_FILE_PATH="/path/to/resume.mv2"
cargo run --release

# Run tests
cargo test

# Check code
cargo clippy -- -D warnings
cargo fmt --check

# Live reload during development
cargo install cargo-watch
cargo watch -x run
```

**Key files:**

- `src/main.rs` - gRPC server, memvid loading
- `src/models.rs` - Data structures
- `proto/memvid.proto` - Service definition
- `Cargo.toml` - Dependencies

---

## Container Development

### Building Locally

```bash
# Frontend only
npm run build  # Creates dist/
podman build -f frontend/Dockerfile -t localhost/ai-resume-frontend:latest frontend/

# API server only
podman build -f api-service/Dockerfile -t localhost/ai-resume-api:latest api-service/

# Memvid service only
podman build -f memvid-service/Dockerfile -t localhost/ai-resume-memvid:latest memvid-service/

# All (multi-arch)
./scripts/build-all.sh latest
```

### Testing Containers Locally

```bash
cd deployment/

# Set up local environment
cp .env.example .env
# Edit .env with your API key

# Run all services
podman-compose up -d

# Check logs
podman-compose logs -f

# Test endpoints
curl http://localhost:8080/health
curl http://localhost:3000/api/v1/health

# Stop
podman-compose down
```

---

## Code Quality Standards

### TypeScript (Frontend)

- Use TypeScript for type safety
- Relaxed checking enabled (`noImplicitAny: false`)
- ESLint configuration in `eslint.config.js`
- Vitest for unit tests

```bash
npm run lint
npm test
npm run build  # Type check included
```

### Python (API)

- Python 3.12+ required
- Type hints recommended (mypy)
- Format with black, isort
- Lint with ruff

```bash
uv run mypy app/
uv run black app/
uv run isort app/
uv run ruff check app/
uv run pytest --cov
```

### Rust (Memvid)

- Follow Rust conventions
- No unsafe code without justification
- No clippy warnings

```bash
cargo fmt
cargo clippy -- -D warnings
cargo test
```

---

## Adding Features

### Adding a New API Endpoint

1. **Define request/response models** in `api-service/app/models.py`:

   ```python
   from pydantic import BaseModel

   class MyRequest(BaseModel):
       query: str

   class MyResponse(BaseModel):
       result: str
   ```

2. **Implement endpoint** in `api-service/app/main.py`:

   ```python
   @app.post("/api/v1/my-endpoint")
   async def my_endpoint(request: MyRequest) -> MyResponse:
       # Implementation
       return MyResponse(result="...")
   ```

3. **Test locally**:

   ```bash
   curl -X POST http://localhost:3000/api/v1/my-endpoint \
     -H "Content-Type: application/json" \
     -d '{"query":"test"}'
   ```

### Adding a New UI Component

1. **Create component** in `src/components/MyComponent.tsx`
2. **Add to layout** in `src/pages/Index.tsx`
3. **Test locally**: `npm run dev`
4. **Build and test container**: `npm run build && podman build ...`

### Updating Resume Data

1. **Edit** `data/profile.example.toml` (template) or user's `profile.toml` (instance config)
2. **Edit** `data/master_resume.md` (content source)
3. **Retrain memvid**: `./scripts/train-memvid.sh`
4. **Test locally**: `podman-compose up -d`
5. **Deploy**: `./scripts/deploy.sh user@server latest`

---

## Testing

### Unit Tests

**Frontend:**

```bash
npm test
npm run test:watch
```

**Python:**

```bash
cd api-service
uv run pytest tests/
uv run pytest --cov=app --cov-report=html
```

**Rust:**

```bash
cd memvid-service
cargo test
cargo test -- --nocapture  # Show println! output
```

### Integration Tests

```bash
# Local compose-based testing
cd deployment/
podman-compose up -d

# Test health endpoints
curl http://localhost:8080/health
curl http://localhost:3000/api/v1/health

# Test chat endpoint
curl -X POST http://localhost:3000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"test","stream":false}'

podman-compose down
```

### Performance Testing

```bash
# Check memvid retrieval speed (<5ms target)
# Measure API response time for chat endpoint
# Monitor container resource usage during load
```

---

## Debugging

### Frontend Debugging

```bash
# Chrome DevTools for live debugging
# React DevTools browser extension recommended
npm run dev  # Vite displays source maps
```

### Python Debugging

```bash
# Using debugger
import pdb; pdb.set_trace()

# Or use VS Code debugger with python extension

# Remote debugging in container
podman exec -it ai-resume-api python -m pdb app/main.py
```

### Rust Debugging

```bash
# Using GDB
rust-gdb target/release/memvid-service

# Or use VS Code with CodeLLDB extension
```

### Container Debugging

```bash
# View logs
podman logs ai-resume-api
podman logs -f ai-resume-memvid  # Follow

# Enter container
podman exec -it ai-resume-api /bin/bash

# Check environment variables
podman exec ai-resume-api env

# Network debugging
podman exec ai-resume-api ping memvid-service
```

---

## Git Workflow

1. **Branch naming**: `feature/description` or `fix/description`
2. **Commit messages**: Clear, imperative tone
3. **PR description**: Explain what and why
4. **Code review**: Self-review before submitting

Example:

```bash
git checkout -b feature/add-export-to-pdf
# Make changes, test locally
git add .
git commit -m "Add PDF export to resume chat"
# Create PR
```

---

## Security Considerations

- **Secrets**: Never commit `.env`, API keys, or credentials
- **Dependencies**: Run `npm audit`, `cargo audit`, `pip check` regularly
- **Input validation**: All user input must be validated
- **Rate limiting**: Protect API endpoints from abuse
- **Container security**: Run as non-root, minimal base images

See [SECURITY.md](./SECURITY.md) for detailed security practices.

---

## Common Issues

### "memvid-service connection refused"

- Ensure Rust service is running: `podman logs ai-resume-memvid`
- Check network: `podman exec ai-resume-api ping memvid-service`
- Verify MEMVID_GRPC_URL environment variable

### "OpenRouter API errors"

- Check API key is set and valid
- Verify model name is correct
- Check API rate limits/quota
- Test directly: `curl https://openrouter.ai/api/v1/models`

### "Build fails with out of memory"

- Use `npm run build` locally before containerizing
- Increase Docker/Podman memory allocation
- Check available disk space

### ".mv2 file not found"

- Run `./scripts/train-memvid.sh` first
- Verify file exists: `ls -la data/.memvid/`
- Check MEMVID_FILE_PATH environment variable

---

## Performance Tips

- Use React Query for efficient data fetching
- Memoize expensive computations with `useMemo`
- Lazy load routes and components
- Compress assets in production builds
- Use CDN for static assets
- Monitor API response times
- Profile with Rust `cargo flamegraph`

---

## Getting Help

- Check [SETUP.md](./SETUP.md) for common setup issues
- Review [PRD.md](./PRD.md) for design decisions
- Check [ARCHITECTURE.md](./ARCHITECTURE.md) for architecture details
- Open an issue on GitHub for bugs
- Discuss features in pull requests
