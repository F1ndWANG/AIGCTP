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

AIGCTP is an AI-native recommendation and planning system for everyday life scenarios. It is designed around a simple product idea: users should be able to describe a real-world need once, and the system should route that request to the right domain workflow, preserve the result, and keep it actionable.

Unlike a single-purpose chatbot, AIGCTP combines conversational AI with structured application modules. A user can ask for a weekend trip, request nearby restaurants, log meals, generate a diet plan, search products, add items to a cart, and return to previous conversations or saved artifacts later.

The project is suitable for:

- multi-agent systems coursework or research prototypes,
- graduation projects and full-stack portfolio demonstrations,
- AI application architecture studies,
- and experiments that connect LLM reasoning with executable business workflows.

## Highlights

- Unified AI entry point for travel, restaurants, diet, commerce, and general conversation.
- Hybrid intent routing with keyword fast paths, LLM semantic classification, clarification handling, and domain dispatch.
- Agent-oriented backend with Supervisor, Dispatcher, Travel, Restaurant, Diet, Commerce, and Cross-Domain composition modules.
- Persistent artifacts for travel plans, restaurant recommendations, diet plans, conversations, carts, orders, feedback, runtime tasks, and domain events.
- Streaming chat support through Server-Sent Events, including progress messages and artifact events.
- Production-oriented service boundaries for context building, conversation storage, artifact synchronization, preference learning, runtime tracking, LLM access, maps, and weather.
- Full-stack user experience with authentication, restored sessions, result cards, business pages, feedback surfaces, and offline/PWA foundations.

## Architecture

```text
Next.js 14 Frontend
  app/
    chat, plans, travel, restaurants, diet, products, cart,
    dashboard, profile, settings, offline
  components/
    Chat, Commerce, Diet, Home, Layout, Map, Restaurant, TravelPlan, UI
        |
        v
FastAPI API Layer
  auth, users, chat, travel, restaurant, diet, commerce,
  feedback, route, runtime
        |
        v
Application Services
  ChatOrchestrator
  ConversationService
  ArtifactService
  ContextBuilder
  PreferenceLearner
  RuntimeService
  LLM / AMap / Weather clients
        |
        v
Agent Layer
  Supervisor -> Dispatcher
    TravelAgent
    RestaurantAgent
    DietAgent
    CommerceAgent
    CrossDomainComposer
        |
        v
Persistence and Infrastructure
  PostgreSQL / SQLite
  Redis
  OpenAI-compatible LLM provider
  AMap
  QWeather
```

## Core Capabilities

### Conversational AI

- Synchronous chat endpoint and SSE streaming endpoint.
- Conversation session creation, listing, restoration, and deletion.
- Context-aware routing that can continue from an active travel plan, restaurant recommendation, diet plan, product result, or cart state.
- General fallback conversation when a request does not belong to a supported business domain.

### Multi-Agent Routing

- `Supervisor` classifies user intent and handles ambiguity.
- `Dispatcher` maps intent to the correct domain agent and loads the minimum required context.
- `TravelAgent`, `RestaurantAgent`, `DietAgent`, and `CommerceAgent` own domain-specific behavior.
- `CrossDomainComposer` combines related outputs, such as travel plans with food or product suggestions.
- `PromptBuilder` and LLM service boundaries keep prompt construction, provider calls, and circuit-breaker behavior isolated from API handlers.

### Travel Planning

- Natural-language itinerary generation.
- Travel plan persistence, listing, detail retrieval, confirmation, and deletion.
- Follow-up adjustment against the current plan.
- Route planning support through the map service layer.
- Weather and location-aware planning hooks.

### Restaurants

- Restaurant recommendation by city, cuisine, and user preference.
- Nearby restaurant search.
- Saved recommendation records.
- Recommendation detail, selection, and deletion workflows.
- Chat-context synchronization for follow-up questions.

### Diet and Health

- Health profile management.
- Meal logging and meal history.
- Meal summary retrieval.
- Diet plan generation, listing, detail retrieval, confirmation, and deletion.
- Nutrition analysis based on recent meal records and user context.

### Commerce

- Product categories, product search, filtering, pagination, and detail views.
- AI-assisted product recommendations.
- Cart creation, item insertion, quantity update, deletion, and clearing.
- Order creation, order listing, detail retrieval, cancellation, status updates, and reorder flow.
- Natural-language cart and reorder intents.

### Feedback and Runtime Observability

- Feedback capture for generated content.
- Feedback statistics and analytics summary endpoints.
- Runtime task records for chat and streaming workflows.
- Domain event records for generated artifacts and execution state.
- Failed task lookup and retry support.

## Tech Stack

| Layer | Technology |
| --- | --- |
| Frontend | Next.js 14, React 18, TypeScript, Tailwind CSS |
| UX and client features | SSE, React Markdown, Leaflet, Serwist/PWA foundation |
| Backend | FastAPI, Pydantic, SQLAlchemy Async ORM |
| Auth | JWT, bcrypt, python-jose |
| Data | PostgreSQL, SQLite-compatible development path |
| Cache | Redis |
| AI | OpenAI-compatible SDK, DeepSeek-compatible configuration |
| External services | AMap, QWeather |
| Testing | Pytest, pytest-asyncio, pytest-cov |
| DevOps | Docker Compose, Uvicorn, environment-based configuration |

## Repository Layout

```text
AIGCTP/
|-- backend/
|   |-- app/
|   |   |-- agents/        # Supervisor, Dispatcher, domain agents, cross-domain composition
|   |   |-- api/           # FastAPI routers for auth, chat, travel, diet, commerce, feedback, runtime
|   |   |-- core/          # Settings, database, Redis, security, logging
|   |   |-- middleware/    # Rate limiting and cross-cutting middleware
|   |   |-- models/        # SQLAlchemy ORM entities
|   |   |-- schemas/       # Pydantic request and response contracts
|   |   `-- services/      # Orchestration, context, artifacts, runtime, LLM, maps, weather
|   |-- tests/             # Backend API and agent tests
|   |-- requirements.txt
|   `-- run.py
|-- frontend/
|   |-- app/               # Next.js App Router pages
|   |-- components/        # Feature and UI components
|   |-- lib/               # API client, session helpers, shared types
|   |-- public/            # Brand assets and static files
|   |-- sw/                # Service worker assets
|   |-- package.json
|   `-- tailwind.config.ts
|-- docker-compose.yml
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

### 1. Clone the repository

```bash
git clone https://github.com/F1ndWANG/AIGCTP.git
cd AIGCTP
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Update `.env` with your own values:

```env
DATABASE_URL=postgresql+asyncpg://lifeai:lifeai_dev@localhost:5432/life_recommender
REDIS_URL=redis://localhost:6379/0
LLM_API_KEY=sk-your-api-key
LLM_API_BASE=https://api.deepseek.com
LLM_MODEL=deepseek-v4-pro
AMAP_API_KEY=your_amap_api_key
QWEATHER_API_KEY=your_qweather_key
JWT_SECRET=replace-with-a-strong-secret
```

### 3. Start infrastructure

```bash
docker compose up -d postgres redis
```

### 4. Run the backend

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
curl http://localhost:8000/api/v1/health/llm
```

### 5. Run the frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

### 6. Docker backend option

The compose file can also run the backend service with PostgreSQL and Redis:

```bash
docker compose up --build
```

## API Surface

All domain APIs are mounted under `/api/v1`.

| Domain | Routes under `/api/v1` |
| --- | --- |
| Auth | `/auth/register`, `/auth/login` |
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

Frontend type and production-build checks:

```bash
cd frontend
npm run build
```

## Design Notes

- API routers are intentionally thin; business workflows live in services and agents.
- Conversation state is persisted separately from generated business artifacts.
- Runtime tasks and domain events make AI execution inspectable and retryable.
- The frontend treats AI output as product state, not disposable text.
- Provider-specific AI calls are isolated behind an OpenAI-compatible service boundary.

## Roadmap

- Add queue-backed asynchronous task execution for long-running agent workflows.
- Introduce richer observability dashboards for runtime tasks and domain events.
- Expand recommendation ranking with learned user preferences.
- Add more robust deployment templates and CI checks.
- Improve map visualization and itinerary collaboration flows.

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
