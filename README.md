# AIGCTP: AI-Driven Life Recommendation and Planning System

<p align="center">
  <img src="frontend/public/brand-banner.svg" width="420" alt="AIGCTP project icon">
</p>

<p align="center">
  <a href="https://github.com/F1ndWANG/AIGCTP"><img src="https://img.shields.io/badge/repo-GitHub-black?logo=github" alt="GitHub Repo"></a>
  <img src="https://img.shields.io/badge/frontend-Next.js%2014-000000?logo=nextdotjs" alt="Next.js 14">
  <img src="https://img.shields.io/badge/backend-FastAPI-009688?logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/language-TypeScript%20%7C%20Python-blue" alt="TypeScript and Python">
  <img src="https://img.shields.io/badge/database-SQLite%20%7C%20PostgreSQL-336791?logo=postgresql" alt="Database">
  <img src="https://img.shields.io/badge/cache-Redis-DC382D?logo=redis" alt="Redis">
  <img src="https://img.shields.io/badge/agent-Multi--Agent-orange" alt="Multi-Agent">
</p>

<p align="center">
  An AI-native decision support system for travel planning, diet management, restaurant recommendation, and commerce-oriented interaction.
</p>

## Overview

`AIGCTP` is a multi-domain intelligent recommendation system designed for daily life decision-making scenarios. Instead of treating conversation as an isolated interface, the project models natural language interaction as an entry point to a set of executable service pipelines, including travel itinerary generation, diet recommendation, restaurant retrieval, route planning, product recommendation, cart operations, and reorder workflows.

From a systems perspective, the project combines:

- a conversational interface for user intent acquisition,
- a supervisor-based routing mechanism for domain dispatch,
- structured storage for persistent user state and generated artifacts,
- and a modular backend that converts language requests into actionable service outputs.

The current implementation is suitable as:

- an AI agent systems course project,
- a graduation project prototype,
- a full-stack portfolio project with real business modules,
- or a baseline for further research on multi-agent recommendation systems.

## Problem Statement

Everyday decision-making is inherently cross-domain, iterative, and context-dependent. However, most consumer applications remain vertically fragmented:

- travel decisions require switching between itinerary tools, maps, weather, and dining platforms;
- diet management requires manual logging, analysis, and plan generation;
- restaurant and product retrieval are usually keyword-driven rather than context-aware;
- recommendation outputs often stop at suggestion generation and do not proceed to downstream actions.

This project addresses that gap by building a unified AI-driven interaction layer that supports the following closed-loop process:

1. Users express needs in natural language.
2. The system performs intent recognition and domain routing.
3. Domain agents generate structured outputs.
4. Results are persisted for later retrieval, refinement, and feedback.
5. Recommendation results can transition into concrete actions such as itinerary follow-up, cart updates, or reorder operations.

## Core Objectives

- Build a unified life-service recommendation platform rather than a single-purpose chatbot.
- Transform free-form user utterances into domain-specific executable operations.
- Persist recommendations as structured entities instead of one-off text outputs.
- Support iterative interaction, feedback collection, and longitudinal user context.
- Provide an engineering-ready full-stack architecture for future optimization and experimentation.

## Implemented Features

### 1. User and Identity Management

- User registration and login
- JWT-based authentication
- Current user profile retrieval
- User profile update
- Password update
- User preference update

### 2. Conversational Interaction and Session Management

- Natural language interaction entry point
- Standard synchronous chat endpoint
- Server-Sent Events streaming chat response
- Conversation session listing
- Session restoration from history
- Session deletion
- General-purpose fallback dialogue for non-domain queries

### 3. Travel Planning Module

- Natural language travel itinerary generation
- Persistent storage of travel plans
- Historical travel plan listing
- Travel plan detail retrieval
- Travel plan deletion
- Iterative travel plan adjustment based on follow-up user instructions
- Route planning API for post-recommendation navigation support

### 4. Diet and Health Module

- Health profile management
- Daily meal logging
- Meal summary retrieval
- Diet plan listing and detail retrieval
- Natural language diet recommendation
- Nutrition analysis workflow

### 5. Restaurant Recommendation Module

- City-based restaurant recommendation
- Cuisine-aware restaurant filtering
- Nearby restaurant query interface
- Independent frontend page for restaurant retrieval

### 6. Commerce and Lightweight Shopping Workflow

- Product category retrieval
- Product search and filtering
- Price range filtering and pagination
- Product detail retrieval
- Cart creation and item insertion
- Cart item quantity update
- Cart item deletion
- Cart clearing
- Order creation and history retrieval
- Order cancellation
- Reorder support
- AI-assisted add-to-cart and reorder intent handling

### 7. Feedback and Analytics

- Recommendation feedback recording
- Like / dislike interaction collection
- Aggregated statistics by content type
- Summary analytics dashboard

### 8. Engineering and Deployment-Oriented Capabilities

- Next.js 14 frontend
- FastAPI backend
- SQLAlchemy async ORM
- SQLite development mode and PostgreSQL compatibility
- Redis integration for cache and middleware capabilities
- API documentation endpoint
- Health check endpoint
- Docker Compose configuration
- PWA-related dependency foundation and offline page support

## Methodological Highlights

### 1. Multi-Agent Routing Instead of Direct Single-Model Reply

The backend does not simply forward user input to an LLM and return the response. It introduces a supervisor-based coordination layer that performs intent classification and dispatches requests to specialized domain agents such as:

- travel agent,
- diet agent,
- restaurant agent,
- commerce agent.

This architectural choice improves task specialization and makes the system easier to extend, benchmark, and refine.

### 2. Structured Recommendation as Persistent State

Generated outputs are treated as application-level entities rather than ephemeral conversational text. Travel plans, diet plans, chat sessions, cart states, and orders can all be persisted, queried, restored, and modified.

This design makes the system more appropriate for:

- stateful recommendation workflows,
- longitudinal personalization,
- and reproducible evaluation of system outputs.

### 3. Actionable Recommendation Pipeline

Many AI demos stop at text generation. This project explicitly extends recommendation into downstream operational steps:

- a travel recommendation can be revisited and adjusted,
- a product recommendation can be added to cart,
- an order can be reordered,
- a dialogue result can be recorded through user feedback.

The result is a more complete human-AI interaction loop.

### 4. Cross-Domain Integration

The system is not limited to a single vertical scenario. It integrates multiple daily life decision domains under one interaction paradigm, which provides a useful baseline for future research directions such as:

- unified user preference modeling,
- cross-domain recommendation transfer,
- hierarchical agent orchestration,
- and contextual memory augmentation.

## System Architecture

```text
User Query
   |
   v
Frontend (Next.js)
   |
   v
Chat / REST API Layer (FastAPI)
   |
   v
Supervisor Agent
   |
   +--> Travel Agent
   +--> Diet Agent
   +--> Restaurant Agent
   +--> Commerce Agent
   +--> General LLM Fallback
   |
   v
Structured Persistence + External Service Calls
   |
   +--> SQLite / PostgreSQL
   +--> Redis
   +--> DeepSeek-compatible LLM API
   +--> AMap API
   +--> QWeather API
```

## Repository Structure

```text
AIGCTP/
|-- backend/
|   |-- app/
|   |   |-- api/          # Authentication, chat, travel, diet, restaurant, commerce, feedback, route, users
|   |   |-- agents/       # Supervisor and domain agents
|   |   |-- core/         # Config, database, security, logging, Redis, cache
|   |   |-- middleware/   # Rate limiting middleware
|   |   |-- models/       # ORM models
|   |   |-- schemas/      # Pydantic schemas
|   |   `-- services/     # LLM, map, weather, truncation services
|   |-- requirements.txt
|   `-- run.py
|-- frontend/
|   |-- app/             # Login, chat, dashboard, diet, restaurants, products, cart, plans, profile, settings
|   |-- components/      # UI and business components
|   |-- lib/             # API client and type definitions
|   `-- package.json
|-- docker-compose.yml
|-- .env.example
`-- start.sh
```

## Screenshots

The following section is prepared for GitHub repository presentation. You can replace the placeholders with real images after uploading screenshots to the repository, for example under `docs/images/`.

```md
![Login Page](docs/images/login.png)
![Chat Interface](docs/images/chat.png)
![Travel Plan Detail](docs/images/travel-plan.png)
![Diet Dashboard](docs/images/diet.png)
![Commerce Module](docs/images/commerce.png)
```

Suggested screenshot set:

- Login page
- Main chat interface with streaming response
- Travel plan detail page
- Diet management page
- Restaurant recommendation page
- Product and cart workflow
- Analytics dashboard

## Tech Stack

### Frontend

- Next.js 14
- React 18
- TypeScript
- Tailwind CSS

### Backend

- FastAPI
- SQLAlchemy Async ORM
- Pydantic
- Redis
- JWT
- bcrypt

### AI and External Services

- OpenAI-compatible SDK with DeepSeek API
- AMap Web API
- QWeather API

## Quick Start

### 1. Environment Variables

Create a `.env` file in the project root:

```env
DATABASE_URL=sqlite+aiosqlite:///./life_recommender.db
LLM_API_KEY=your_api_key
LLM_API_BASE=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
AMAP_API_KEY=your_amap_key
QWEATHER_API_KEY=your_qweather_key
JWT_SECRET=your_jwt_secret
DEBUG=true
```

### 2. Start the Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Backend endpoints:

- `http://localhost:8000`
- `http://localhost:8000/docs`

### 3. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend endpoint:

- `http://localhost:3000`

## Research and Extension Directions

Possible future work includes:

- finer-grained user preference modeling,
- prompt optimization and recommendation quality evaluation,
- stronger failure handling and degradation strategies for external APIs,
- expanded automated test coverage,
- deployment hardening and observability,
- and comparative evaluation of intent classification and routing strategies.

## Project Value

This repository demonstrates more than UI integration. It provides a practical baseline for studying how natural language interfaces can coordinate structured multi-domain service execution. In that sense, it can serve both as an engineering artifact and as an experimental scaffold for AI agent system design.

## License

License information can be added before or after open-source publication on GitHub.
