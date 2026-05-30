"""Unit tests for gateway health endpoint."""

import sys
from pathlib import Path

import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport

import nats

# Add gateway root to sys.path so its `app` package is importable
_SERVICE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_SERVICE_ROOT))

# Remove any cached `app` module from other services
for key in list(sys.modules.keys()):
    if key == "app" or key.startswith("app."):
        del sys.modules[key]

from app.main import app as fastapi_app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_health_endpoint():
    """Health endpoint returns service info."""
    with patch.object(nats, "connect", new_callable=AsyncMock) as mock_connect:
        mock_nc = AsyncMock()
        mock_connect.return_value = mock_nc

        transport = ASGITransport(app=fastapi_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "gateway"
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"
    assert "timestamp" in data
