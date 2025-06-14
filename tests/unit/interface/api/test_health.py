import pytest
from fastapi.testclient import TestClient

from delivery_hours_service.interface.app import Application


@pytest.fixture
def test_client():
    app = Application()
    return TestClient(app.get_app())


def test_health_endpoint_returns_healthy_status(test_client):
    response = test_client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "delivery-hours-service"
    assert data["version"] == "1.0.0"
