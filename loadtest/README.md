# Load Testing with k6

This directory contains [k6](https://k6.io) scripts for performance and load testing the AIGCTP API.

## Prerequisites

- [k6](https://k6.io/docs/get-started/installation/) installed locally
- Backend running (see `docker compose -f docker-compose.prod.yml up`)

## Quick Start

```bash
# Run a smoke test (5 VUs, 30s)
k6 run loadtest/scenario.ts

# Run with custom URL and LLM key
BASE_URL=https://your-domain.com \
LLM_API_KEY=sk-xxx \
k6 run loadtest/scenario.ts
```

## Test Scenario

The script simulates realistic user behaviour:

1. **Register & Login** — creates a unique user, authenticates
2. **Chat** — sends 5 different messages (greeting, diet query, travel plan, etc.)
3. **Profile** — GET and update user profile/preferences
4. **Runtime** — list task runs
5. **Health** — liveness and readiness checks

## Metrics

| Metric | What it measures |
|--------|-----------------|
| `auth_duration` | Auth endpoint response time |
| `chat_duration` | Chat endpoint response time (includes LLM calls) |
| `auth_failures` | Auth failure rate |
| `chat_failures` | Chat failure rate |

## Thresholds

- 95% of requests complete within 5s
- Failure rate below 10%
- Auth P95 under 2s
- Chat P95 under 30s (includes LLM generation time)
