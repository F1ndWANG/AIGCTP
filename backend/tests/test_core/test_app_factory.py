import pytest
from httpx import ASGITransport, AsyncClient

from app.app_factory import create_app
from app.api.router import API_ROUTERS
from app.core.app_info import APP_TITLE
from app.core.http_paths import API_METRICS_PATH, API_V1_PREFIX, HEALTH_PATH


@pytest.mark.anyio
async def test_create_app_registers_operational_routes():
    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(HEALTH_PATH)

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["X-Request-ID"]


def test_create_app_registers_api_and_ops_routes():
    app = create_app()
    paths = {route.path for route in app.routes}

    assert app.title == APP_TITLE
    assert HEALTH_PATH in paths
    assert API_METRICS_PATH in paths
    assert "/api/v1/chat" in paths
    assert "/api/v1/recommend/feed" in paths


def test_api_router_registry_is_not_empty_and_uses_v1_prefix():
    app = create_app()
    paths = {route.path for route in app.routes}

    assert len(API_ROUTERS) >= 10
    assert any(path.startswith(f"{API_V1_PREFIX}/auth") for path in paths)
    assert any(path.startswith(f"{API_V1_PREFIX}/shares") for path in paths)
