# AI Resume

Transform your static resume into an interactive AI-powered conversation.

![AI Resume Screenshot](frontend/public/ai-resume.png)

## Who Is This For?

**Resume Owner** - Deploy your resume as an AI agent that can answer questions about your experience, assess job fit, and have natural conversations with visitors.

**Recruiter / Hiring Manager** - Get instant, thoughtful answers about a candidate. Ask about specific skills, experience relevance, or job fit. No more scanning PDFs.

## Documentation

| Document | Description |
| -------- | ----------- |
| [Setup](docs/SETUP.md) | Installation, building, deployment |
| [Architecture](docs/ARCHITECTURE.md) | System design, data flow, network topology |
| [PRD](docs/PRD.md) | Product requirements, success metrics |
| [Development](docs/DEVELOPMENT.md) | Contributing guide, workflows |
| [Master Document Schema](docs/MASTER_DOCUMENT_SCHEMA.md) | Resume markdown format |
| [Agentic Flow](docs/AGENTIC_FLOW.md) | LLM orchestration and prompt design |
| [Security](docs/SECURITY.md) | Security hardening, vulnerability management |
| [Test Coverage](docs/TEST_COVERAGE.md) | Test strategy and coverage reports |
| [TODO](docs/TODO.md) | Roadmap and task breakdown |

## Quick Start

```bash
# 1. Create your resume data
cp data/example_resume.md data/master_resume.md
# Edit with your information

# 2. Ingest into memvid
cd ingest && uv run python ingest.py --verify

# 3. Deploy
cd deployment && podman-compose up -d
```

See [docs/SETUP.md](docs/SETUP.md) for complete instructions.

## License

PolyForm Noncommercial License 1.0.0 - See LICENSE file
