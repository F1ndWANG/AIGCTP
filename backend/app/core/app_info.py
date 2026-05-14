"""Application metadata for the FastAPI runtime and generated docs."""

APP_TITLE = "AIGCTP — AI Life Recommender API"
APP_VERSION = "0.1.0"
APP_DESCRIPTION = """Multi-agent lifestyle recommendation platform.

Features:
* **Travel Planning** — multi-day itinerary generation with POI, weather, budget
* **Diet & Nutrition** — meal logging, nutrition analysis, diet plan generation
* **Restaurant Recommendations** — personalised restaurant search
* **Commerce** — product recommendations, shopping cart, ordering
* **Multi-Agent Architecture** — supervisor classifies intent, dispatcher routes to domain agents
* **Async Workers** — arq-powered background job queue for heavy operations
"""


def fastapi_metadata() -> dict:
    return {
        "title": APP_TITLE,
        "description": APP_DESCRIPTION,
        "version": APP_VERSION,
        "contact": {"name": "AIGCTP Team", "url": "https://github.com/your-org/aigctp"},
        "license_info": {"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
        "docs_url": "/docs",
        "redoc_url": "/redoc",
    }
