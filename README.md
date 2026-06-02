# OpenEye — AI-Powered CCTV Monitoring System

Real-time video/image analysis using vision AI models. Stays quiet during normal activity, alerts on dangerous situations (violence, weapons, etc.).

## Architecture

- **Gateway** — FastAPI REST + WebSocket entry point
- **Guardrails** — LLM input/output security (separate microservice)
- **Analyzer** — Vision model inference via LiteLLM (Ollama/OpenAI/Anthropic)
- **Ingestor** — Video file frame extraction
- **Alerter** — Alert filtering, persistence, webhook/WebSocket delivery
- **Dashboard** — Next.js real-time UI with webcam support

Inter-service messaging via **NATS + JetStream**.

## Quick Start

```bash
# Copy environment config
cp .env.example .env

# Start all services (infra → init → apps)
make up

# Gateway API: http://localhost:8000
# Dashboard:   http://localhost:3000
# NATS monitor: http://localhost:8222

# Run tests (60 unit tests in Docker)
make test
```

## Features

- **Real-time Analysis** — WebSocket streaming for live webcam monitoring
- **Multi-Model Support** — Ollama (LLaVA, Moondream), OpenAI (GPT-4o), Anthropic (Claude)
- **Smart Alerting** — Severity-based filtering, deduplication, configurable thresholds
- **Guardrails** — Input validation, rate limiting, PII redaction, output sanitization
- **Video Ingest** — RTSP/webcam frame capture with configurable FPS and quality
- **Modern Dashboard** — Next.js UI with live alerts feed, webcam view, config panel
- **Persistent Storage** — PostgreSQL for alerts and audit logs
- **Microservices** — Fully containerized, horizontally scalable architecture

## Requirements

- Docker & Docker Compose
- Ollama running on host with `llava` model pulled:
  ```bash
  ollama pull llava
  ```

## Project Structure

```
openeye/
├── docker-compose.yml       # All services + infrastructure
├── services/
│   ├── gateway/             # API gateway (FastAPI)
│   ├── guardrails/          # LLM security service
│   ├── analyzer/            # Vision model inference
│   ├── ingestor/            # Video processing
│   └── alerter/             # Alert delivery
├── dashboard/               # Next.js frontend
├── shared/                  # Shared schemas & config
├── scripts/                 # Init scripts (NATS setup)
└── migrations/              # PostgreSQL schema
```

## Configuration

Key environment variables (see `.env.example` for full list):

```bash
# Model Configuration
MODEL_PROVIDER=ollama              # ollama, openai, anthropic
MODEL_MODEL=llava                  # Model name
MODEL_API_BASE=http://host.docker.internal:11434
LLM_MODELS=llava,llava:13b,moondream  # Available models in dashboard

# Ingestor (RTSP/Webcam)
INGESTOR_SOURCES=0                 # Comma-separated: 0 (webcam), rtsp://...
INGESTOR_FPS=1.0                   # Frames per second
INGESTOR_JPEG_QUALITY=85           # JPEG compression quality

# Alerting
ALERT_SEVERITY_THRESHOLD=6         # Min severity to trigger alert (0-10)
ALERT_DEDUP_WINDOW_SECONDS=30      # Deduplication window
ALERT_WEBHOOK_URLS=                # Comma-separated webhook URLs

# Guardrails
GUARDRAILS_MAX_FILE_SIZE_MB=5
GUARDRAILS_RATE_LIMIT_PER_SOURCE=2.0  # Requests per second
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service health check |
| POST | `/analyze` | Upload image for analysis |
| WS | `/ws/stream` | Real-time webcam analysis |
| GET | `/alerts` | Query alerts (pagination, severity filter) |
| GET | `/alerts/count` | Alert count |
| GET | `/config/models` | Available LLM models |

## Pipeline

```
Ingestor (RTSP/device) → frames.new → Guardrails → frames.validated → Analyzer → analysis.results → Alerter → PostgreSQL
Gateway (WS/REST) → rpc.analyze → Analyzer → response
```

## Development

Each service can be developed independently. All communicate via NATS subjects:

| Subject | Purpose |
|---------|---------|
| `frames.new` | Raw frames from webcam/ingestor |
| `frames.validated` | Guardrails-validated frames |
| `analysis.results` | Validated analysis results |
| `alerts.new` | Triggered alerts |
| `rpc.analyze` | Synchronous request/reply analysis |

## Testing

```bash
# Run all 60 unit tests in Docker
make test

# Test individual services
docker compose -f docker-compose.test.yml run --rm test pytest services/gateway/tests -v
docker compose -f docker-compose.test.yml run --rm test pytest services/analyzer/tests -v
```

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make up` | Start all services (infra → init → apps) |
| `make down` | Stop all services |
| `make test` | Run 60 unit tests in Docker |
| `make clean` | Remove containers, volumes, images |
| `make logs` | Tail all service logs |
| `make ps` | Show running containers |
| `make init-nats` | Re-provision NATS JetStream streams |
| `make init-db` | Re-run database migrations |

## Tech Stack

- **Backend**: Python 3.12, FastAPI, asyncio, asyncpg
- **AI/ML**: LiteLLM, Ollama, OpenAI, Anthropic
- **Messaging**: NATS 2.10 + JetStream
- **Database**: PostgreSQL 16
- **Cache**: Redis 7
- **Frontend**: Next.js 14, React, TypeScript, Tailwind CSS
- **Infra**: Docker, Docker Compose

## License

MIT
