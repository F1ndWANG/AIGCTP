# AIGCTP: AI Life Recommendation and Planning Platform

<p align="center">
  <img src="frontend/public/brand-banner.svg" width="420" alt="AIGCTP project icon">
</p>

<p align="center">
  <a href="https://github.com/F1ndWANG/AIGCTP"><img src="https://img.shields.io/badge/repo-GitHub-black?logo=github" alt="GitHub Repo"></a>
  <img src="https://img.shields.io/badge/frontend-Next.js%2014-000000?logo=nextdotjs" alt="Next.js 14">
  <img src="https://img.shields.io/badge/backend-FastAPI-009688?logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/language-TypeScript%20%7C%20Python-blue" alt="TypeScript and Python">
  <img src="https://img.shields.io/badge/database-PostgreSQL%20%7C%20SQLite-336791?logo=postgresql" alt="Database">
  <img src="https://img.shields.io/badge/cache-Redis-DC382D?logo=redis" alt="Redis">
  <img src="https://img.shields.io/badge/AI-Multi--Agent-orange" alt="Multi-Agent">
</p>

<p align="center">
  A full-stack, multi-agent life-service platform that turns natural-language requests into travel plans, restaurant recommendations, diet guidance, product discovery, cart actions, and persistent business artifacts.
</p>

## Overview

AIGCTP is a full-stack AI life-service platform. It combines a conversational entry point with structured product modules so that one natural-language request can become a saved travel plan, restaurant recommendation, diet plan, product recommendation, cart operation, order workflow, or reusable conversation artifact.

The system is intentionally built as an application rather than a standalone chatbot. The frontend presents concrete business pages for authentication, chat, travel, restaurants, diet, products, cart, dashboard, profile, and settings. The backend keeps HTTP handlers thin, routes AI requests through a supervisor and dispatcher, persists generated artifacts, records runtime events, and exposes normal REST APIs for every domain.

The current development setup is optimized for local demo readiness. Redis can fall back to an in-memory backend, third-party map keys can fall back to curated demo POI and restaurant data, and generated AI artifacts are synchronized into normal app pages such as travel plans, restaurant recommendations, products, and carts.

The project is useful for:

- AI application architecture demonstrations.
- Multi-agent routing and orchestration experiments.
- Full-stack portfolio or course projects.
- Prototypes that connect LLM reasoning with persistent business workflows.

## Key Features

- Unified AI chat entry point for travel, restaurants, diet, commerce, and general conversation.
- Hybrid intent classification with keyword fast paths, LLM semantic classification, parameter extraction, and clarification prompts.
- Multi-agent backend with Supervisor, Dispatcher, TravelAgent, RestaurantAgent, DietAgent, CommerceAgent, and CrossDomainComposer.
- Server-Sent Events streaming for chat progress, model tokens, final results, and generated artifacts.
- Centralized frontend API client with request timeouts, retry handling, token refresh, and shared auth recovery for REST and streaming calls.
- Persistent application artifacts for conversations, travel plans, restaurant recommendations, health profiles, meal records, diet plans, products, carts, orders, feedback, task runs, and domain events.
- JWT authentication with refresh tokens, login lockout support, password hashing, and user preference storage.
- Development-friendly Redis fallback with production-ready Redis cache and async job infrastructure.
- Production-oriented middleware for CORS, request IDs, rate limiting, security headers, metrics, logging, and readiness checks.
- Local AMap fallback data for demo travel POIs and restaurant search when external keys are not configured.
- Next.js PWA foundation using Serwist service worker assets.
- Polished authentication shell, responsive dashboard, persistent navigation, and generated product image assets for the commerce catalog.
- Docker Compose, production Compose, Kubernetes manifests, Nginx config, load-test assets, and monitoring dashboard artifacts.

## Architecture

```text
Client Browser
  |
  v
Next.js 14 Frontend
  app/              pages and routes
  components/       feature and UI components
  lib/api.ts        typed API client, token refresh, retry handling, SSE parsing
  next.config.js    /api/* rewrite to FastAPI /api/v1/*
  |
  v
FastAPI Backend
  app/main.py       application startup, middleware, router registration
  app/api/          auth, users, chat, travel, restaurant, diet, commerce,
                   feedback, route, runtime
  |
  v
Application Services
  ChatOrchestrator          request workflow and SSE event generation
  ConversationService       session persistence and restoration
  ArtifactService           generated artifact synchronization
  RuntimeService            task runs, domain events, retry metadata
  PreferenceLearner         user preference extraction and storage
  LLM / AMap / Weather      external provider boundaries and local fallbacks
  |
  v
Agent Layer
  Supervisor                intent classification and clarification
  Dispatcher                intent-to-agent routing
  TravelAgent               itinerary generation and adjustment
  RestaurantAgent           restaurant recommendation
  DietAgent                 meal logging, nutrition analysis, diet plans
  CommerceAgent             product recommendation, cart and reorder intents
  CrossDomainComposer       combined travel, food, and product results
  |
  v
Persistence and Infrastructure
  PostgreSQL / SQLite       relational application data
  Redis / InMemoryRedis     cache, rate limit state, background queue, dev fallback
  arq Worker                async chat and long-running domain jobs
  OpenAI-compatible LLM     DeepSeek-compatible default configuration
  AMap / QWeather           maps, POI, route, and weather data with demo fallback paths
```

## Request Flow

### Streaming Chat

```text
frontend chat.sendStream()
  -> POST /api/chat/stream
  -> Next.js rewrite to /api/v1/chat/stream
  -> FastAPI chat router
  -> ChatOrchestrator.stream_chat_events()
  -> Supervisor intent classification
  -> Dispatcher domain routing
  -> Domain agent execution
  -> Artifact persistence and runtime event emission
  -> SSE events back to the browser
```

The stream can emit thinking messages, LLM tokens, final text, travel plans, restaurant recommendations, diet plans, product results, cart items, errors, and completion events.

### Non-Streaming Chat

```text
frontend chat.send()
  -> POST /api/chat
  -> shared request client handles timeout, retry, and auth refresh
  -> ChatOrchestrator.handle_chat()
  -> Supervisor and Dispatcher
  -> Agent result
  -> saved conversation and artifacts
  -> ChatResponse
```

### Domain APIs

The app does not rely only on chat. Each business area also has direct REST endpoints so generated artifacts can be listed, opened, updated, confirmed, deleted, retried, or reused from normal pages.

## Capabilities

### Conversational AI

- Synchronous and streaming chat endpoints.
- Conversation creation, listing, restoration, and deletion.
- Session-aware follow-up handling.
- Context-aware continuation from saved travel plans and generated artifacts.
- General fallback conversation when no supported business intent is detected.

### Multi-Agent Routing

- `Supervisor` classifies user intent and handles ambiguity.
- `Dispatcher` maps intents to domain agents and loads the required context.
- Keyword and LLM classifiers cooperate to reduce cost while keeping flexible natural-language handling.
- Clarification responses are returned when intent confidence or required parameters are insufficient.
- Cross-domain composition can enrich travel results with food or product suggestions.

### Travel Planning

- Natural-language itinerary generation.
- Follow-up plan adjustment against the current itinerary.
- Streaming chat artifact persistence so generated plans appear in the travel-plan pages.
- Travel plan listing, detail retrieval, confirmation, and deletion.
- POI search, route planning, and weather-aware itinerary hooks.
- Travel memory for excluded or requested POIs across follow-up messages.

### Restaurants

- Restaurant recommendation by city, cuisine, and dietary context.
- Nearby restaurant recommendation path.
- Curated local restaurant fallback for common demo cities when AMap is not configured.
- Saved recommendation records.
- Recommendation detail, selection, and deletion workflows.

### Diet and Health

- Health profile management.
- Meal logging and meal history.
- Meal summary and nutrition analysis.
- Diet plan generation, listing, detail retrieval, confirmation, and deletion.
- Health-profile-aware recommendations.

### Commerce

- Product categories, product search, filtering, pagination, and detail views.
- AI-assisted product recommendations.
- Local generated product image assets for the seeded catalog.
- Cart creation, item insertion, quantity update, deletion, and clearing.
- Order creation, listing, detail retrieval, cancellation, status updates, and reorder flow.
- Natural-language auto-cart and quick reorder intents.

### Feedback and Runtime Observability

- Feedback capture for generated content.
- Feedback statistics and analytics summary endpoints.
- Runtime task records for chat and background workflows.
- Domain event records for generated artifacts and execution state.
- Failed task lookup and retry support.
- Metrics endpoint and Grafana dashboard artifact.

## Tech Stack

| Layer | Technology |
| --- | --- |
| Frontend | Next.js 14, React 18, TypeScript, Tailwind CSS |
| UX and client features | SSE, React Markdown, Leaflet, Serwist/PWA foundation |
| Backend | FastAPI, Pydantic, SQLAlchemy Async ORM |
| Auth | JWT, bcrypt, python-jose |
| Data | PostgreSQL, SQLite-compatible development path |
| Cache | Redis with development in-memory fallback |
| Background jobs | arq worker on Redis |
| AI | OpenAI-compatible SDK, DeepSeek-compatible configuration |
| External services | AMap, QWeather, local demo fallbacks |
| Testing | Pytest, pytest-asyncio, pytest-cov |
| Frontend testing | Playwright |
| DevOps | Docker Compose, production Compose, Kubernetes, Nginx, Uvicorn |

## Repository Layout

```text
AIGCTP/
|-- backend/
|   |-- alembic/           # Database migrations
|   |-- app/
|   |   |-- agents/        # Supervisor, Dispatcher, domain agents, cross-domain composition
|   |   |-- api/           # FastAPI routers
|   |   |-- core/          # Settings, database, Redis, security, logging, metrics
|   |   |-- middleware/    # Rate limiting and security headers
|   |   |-- models/        # SQLAlchemy ORM entities
|   |   |-- schemas/       # Pydantic request and response contracts
|   |   |-- services/      # Orchestration, context, artifacts, runtime, LLM, maps, weather, demo fallbacks
|   |   |-- jobs.py        # arq background job definitions
|   |   `-- main.py        # FastAPI app entry point
|   |-- tests/             # Backend API and agent tests
|   |-- requirements.txt
|   |-- requirements-dev.txt
|   |-- run.py
|   `-- run_worker.py
|-- frontend/
|   |-- app/               # Next.js App Router pages
|   |-- components/        # Feature and UI components
|   |-- lib/               # API client, session helpers, shared types
|   |-- public/            # Brand assets, product images, and static files
|   |-- sw/                # Service worker assets
|   |-- package.json
|   |-- playwright.config.ts
|   `-- tailwind.config.ts
|-- docs/                  # Project documentation
|-- k8s/                   # Kubernetes manifests
|-- loadtest/              # Load-test assets
|-- monitoring/            # Grafana dashboard artifact
|-- nginx/                 # Reverse proxy configuration
|-- docker-compose.yml
|-- docker-compose.prod.yml
|-- docker-compose.e2e.yml
|-- .env.example
|-- start.sh
`-- README.md
```

## Getting Started

### Prerequisites

- Node.js 20+
- Python 3.11+
- Docker and Docker Compose
- PostgreSQL and Redis, or the provided Docker Compose services
- API keys for your LLM provider, AMap, and QWeather if you want full external-service behavior
- For local demos, `REDIS_URL=memory://` and placeholder AMap/QWeather keys are supported with graceful fallbacks

### 1. Clone

```bash
git clone https://github.com/F1ndWANG/AIGCTP.git
cd AIGCTP
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Update `.env` with your own values:

```env
DATABASE_URL=postgresql+asyncpg://lifeai:lifeai_dev@localhost:5432/life_recommender
REDIS_URL=memory://
LLM_API_KEY=sk-your-api-key
LLM_API_BASE=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
AMAP_API_KEY=your_amap_api_key
QWEATHER_API_KEY=your_qweather_key
JWT_SECRET=replace-with-a-strong-secret
```

Use `REDIS_URL=redis://localhost:6379/0` when a real Redis service is available. In production, configure real Redis, AMap, QWeather, and a strong JWT secret.

### 3. Start Infrastructure

```bash
docker compose up -d postgres redis
```

### 4. Run Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend health checks:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/health/ready
curl http://localhost:8000/api/v1/health/llm
```

### 5. Run Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

### 6. Optional Background Worker

For background chat or long-running jobs:

```bash
cd backend
python run_worker.py
```

### 7. Docker Compose Option

The compose file can also run the backend service with PostgreSQL and Redis:

```bash
docker compose up --build
```

For the production-style stack:

```bash
docker compose -f docker-compose.prod.yml up --build
```

## API Surface

All domain APIs are mounted under `/api/v1`.

| Domain | Routes under `/api/v1` |
| --- | --- |
| Auth | `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout` |
| Users | `/users/me`, `/users/me/password`, `/users/me/preferences` |
| Chat | `/chat`, `/chat/stream`, `/chat/sessions` |
| Travel | `/travel/plans`, `/travel/plans/{id}`, confirmation and deletion |
| Restaurants | `/restaurant/recommend`, `/restaurant/nearby`, saved recommendations |
| Diet | `/diet/profile`, `/diet/meals`, `/diet/plans` |
| Commerce | `/commerce/categories`, `/commerce/products`, `/commerce/cart`, `/commerce/orders` |
| Feedback | `/feedback`, `/feedback/stats`, `/feedback/analytics/summary` |
| Route | `/route` |
| Runtime | `/runtime/tasks`, `/runtime/events`, task retry endpoints |

FastAPI also exposes interactive API documentation at:

```text
http://localhost:8000/docs
```

## Configuration

Important environment variables:

| Variable | Purpose |
| --- | --- |
| `APP_ENV` | `development`, `staging`, or `production` |
| `DEBUG` | Enables verbose development behavior |
| `DATABASE_URL` | SQLAlchemy async database URL |
| `REDIS_URL` | Redis URL for cache, rate limit state, and jobs; `memory://` is supported for local development |
| `CORS_ORIGINS` | Comma-separated allowed frontend origins |
| `LLM_API_KEY` | API key for the OpenAI-compatible provider |
| `LLM_API_BASE` | Provider base URL, DeepSeek-compatible by default |
| `LLM_MODEL` | Primary model name, currently configured for `deepseek-v4-flash` in development |
| `LLM_FALLBACK_MODEL` | Optional fallback model |
| `AMAP_API_KEY` | AMap API key; placeholder values use local demo fallback data in development |
| `QWEATHER_API_KEY` | QWeather API key; placeholder values use weather fallback behavior in development |
| `JWT_SECRET` | Secret used to sign tokens |
| `TRUSTED_PROXIES` | Trusted proxy CIDRs for production deployments |

## Testing

Run backend tests from the `backend` directory:

```bash
pytest
```

Useful focused runs:

```bash
pytest tests/test_agents
pytest tests/test_api
pytest --cov=app
```

Frontend build and e2e checks:

```bash
cd frontend
npm run build
npm run test:e2e
```

Local smoke check without Docker/k6:

```bash
python scripts/smoke_test.py --base-url http://127.0.0.1:8000
```

PostgreSQL-specific integration tests require a real PostgreSQL URL:

```bash
cd backend
DATABASE_URL=postgresql+asyncpg://lifeai:lifeai_dev@localhost:5432/life_recommender_test pytest tests/test_integration -q
```

On Windows, initialize the default local PostgreSQL test role/database first:

```powershell
.\scripts\setup-local-postgres.ps1
```

## Deployment Notes

- `docker-compose.yml` is suitable for local infrastructure and backend development.
- `docker-compose.prod.yml` includes frontend, backend, worker, Nginx, PostgreSQL, and Redis.
- `k8s/` contains manifests for namespace, config, secrets, deployments, services, ingress, HPA, PostgreSQL, and Redis.
- `nginx/nginx.conf` provides a reverse proxy entry point for production Compose.
- `monitoring/grafana-dashboard.json` contains a dashboard artifact for runtime visibility.
- `loadtest/` contains load-test documentation and assets.

## Design Principles

- API routers are intentionally thin; business workflows live in services and agents.
- Conversation state is persisted separately from generated business artifacts.
- Runtime tasks and domain events make AI execution inspectable and retryable.
- The frontend treats AI output as product state, not disposable text.
- Provider-specific AI calls are isolated behind an OpenAI-compatible service boundary.
- Frontend transport concerns such as token storage, refresh, retries, and SSE parsing are centralized in one API client.
- Domain agents return structured results that can be saved, displayed, and reused by normal pages.
- Infrastructure concerns such as caching, metrics, rate limits, and security headers are centralized.

## Roadmap

- Harden background job execution and retry behavior for more long-running workflows.
- Expand observability dashboards for runtime tasks, domain events, and LLM provider health.
- Expand recommendation ranking with learned user preferences.
- Improve map visualization, itinerary collaboration, and route comparison flows.
- Add broader CI coverage for backend tests, frontend builds, and Playwright e2e flows.
- Add migration and release documentation for production deployments.

## Contributing

Contributions are welcome. For substantial changes, open an issue first to discuss the proposed behavior and implementation plan.

Recommended workflow:

1. Fork the repository.
2. Create a focused feature branch.
3. Add or update tests for behavioral changes.
4. Run the relevant backend and frontend checks.
5. Open a pull request with a clear summary and validation notes.

## License

No license file is currently included. Add a license before distributing or reusing this project outside its current repository context.
