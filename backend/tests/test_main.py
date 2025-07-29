import pytest
from fastapi.testclient import TestClient
from main import app, redis

client = TestClient(app)

@pytest.mark.asyncio
async def test_save_progress():
    # Mock authenticated user
    user_id = "test_user"
    progress = {"step": 1, "data": {"email": "test@example.com"}}
    response = client.post("/api/v1/onboarding/progress", json=progress, headers={"Authorization": "Bearer mock_token"})
    assert response.status_code == 200
    assert response.json() == {"status": "success"}

@pytest.mark.asyncio
async def test_get_progress():
    user_id = "test_user"
    response = client.get("/api/v1/onboarding/progress", headers={"Authorization": "Bearer mock_token"})
    assert response.status_code == 200
    assert "step" in response.json()