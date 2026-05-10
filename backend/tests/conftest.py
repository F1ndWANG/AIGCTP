"""Test fixtures: engine, session, client, auth headers, and mocked external services."""
import asyncio
import pytest
from typing import AsyncGenerator

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app
from app.core.security import create_access_token, hash_password
from app.models.user import User

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="function")
def event_loop():
    """Per-function event loop for complete test isolation."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def engine():
    """Per-function engine — each test gets a fresh in-memory database."""
    e = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with e.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield e
    await e.dispose()


@pytest.fixture
async def session(engine) -> AsyncGenerator[AsyncSession, None]:
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as s:
        yield s


@pytest.fixture
async def client(session) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(session) -> User:
    user = User(
        username="testuser",
        hashed_password=hash_password("testpass123"),
        display_name="Test User",
        preferences={"theme": "dark", "language": "zh"},
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user) -> dict:
    token = create_access_token(test_user.id)
    return {"Authorization": f"Bearer {token}"}


# ── Mock all external API calls ──

@pytest.fixture(autouse=True)
def mock_external_services(monkeypatch):
    """Mock external APIs: LLM, Amap, QWeather."""

    async def mock_chat(*args, **kwargs):
        return "这是一个测试回复内容。"

    async def mock_chat_stream(*args, **kwargs):
        yield "测试"
        yield "回复"

    async def mock_extract_json(*args, **kwargs):
        return {"intent": "general_chat", "extracted_info": {}}

    async def mock_chat_with_artifact(*args, **kwargs):
        return {
            "text": "这是一个测试回复内容。",
            "artifact": {
                "destination": "北京",
                "days": 2,
                "theme": "测试行程",
                "day_by_day": [
                    {
                        "day": 1,
                        "theme": "第一天测试",
                        "weather": {"condition": "晴", "temp_min": "18", "temp_max": "28"},
                        "meals": [],
                        "activities": [
                            {"time": "上午", "poi": "故宫博物院", "duration": "2小时"},
                            {"time": "下午", "poi": "雍和宫", "duration": "2小时"},
                        ],
                        "shopping": [],
                        "hotel": {},
                        "transport_tips": "",
                    },
                    {
                        "day": 2,
                        "theme": "第二天测试",
                        "weather": {"condition": "晴", "temp_min": "18", "temp_max": "28"},
                        "meals": [],
                        "activities": [
                            {"time": "上午", "poi": "颐和园", "duration": "2小时"},
                            {"time": "下午", "poi": "圆明园", "duration": "2小时"},
                        ],
                        "shopping": [],
                        "hotel": {},
                        "transport_tips": "",
                    },
                ],
                "budget_estimate": {"total": "待定"},
                "tips": [],
            },
        }

    monkeypatch.setattr("app.services.llm.llm_service.chat", mock_chat)
    monkeypatch.setattr("app.services.llm.llm_service.chat_stream", mock_chat_stream)
    monkeypatch.setattr("app.services.llm.llm_service.extract_json", mock_extract_json)
    monkeypatch.setattr("app.services.llm.llm_service.chat_with_artifact", mock_chat_with_artifact)

    async def mock_search_poi(*args, **kwargs):
        return [{
            "poi_id": "TEST001",
            "name": "测试景点",
            "longitude": 104.0,
            "latitude": 30.5,
            "category": "风景名胜",
            "address": "测试地址",
            "rating": "4.5",
            "phone": "",
            "opening_hours": "09:00-18:00",
            "images": [],
            "tags": ["景点", "旅游"],
        }]

    async def mock_get_direction(*args, **kwargs):
        return {
            "distance": "5000",
            "duration": "1800",
            "steps": [{"instruction": "步行100米", "distance": "100", "duration": "120"}],
        }

    async def mock_geocode(*args, **kwargs):
        return {"longitude": 104.0, "latitude": 30.5, "formatted_address": "测试地址"}

    monkeypatch.setattr("app.services.amap.amap_service.search_poi", mock_search_poi)
    monkeypatch.setattr("app.services.amap.amap_service.search_restaurants", mock_search_poi)
    monkeypatch.setattr("app.services.amap.amap_service.search_hotels", mock_search_poi)
    monkeypatch.setattr("app.services.amap.amap_service.search_around", mock_search_poi)
    monkeypatch.setattr("app.services.amap.amap_service.get_direction", mock_get_direction)
    monkeypatch.setattr("app.services.amap.amap_service.geocode", mock_geocode)

    async def mock_weather(*args, **kwargs):
        return [{
            "date": "2026-05-04",
            "temp_max": "28",
            "temp_min": "18",
            "condition": "晴",
            "wind_dir": "东南风",
        }]

    monkeypatch.setattr(
        "app.services.weather.qweather_service.get_weather_forecast", mock_weather
    )
