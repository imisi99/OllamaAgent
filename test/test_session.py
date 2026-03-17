from datetime import datetime
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import MagicMock, patch
from main import app


global sess_id

sess_id = ""


@pytest.mark.asyncio
async def test_create_session():
    llm_mock = MagicMock()
    llm_mock.content = "Testing the Create Session"

    with patch("app.session.get_llm") as mock_llm:
        mock_llm.return_value.invoke.return_value = llm_mock

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            body = {
                "session_id": "",
                "message": {
                    "content": "hello, i'm running a test",
                    "role": "user",
                    "timestamp": datetime.now().isoformat(),
                },
            }
            response = await ac.post("/session/create", json=body)
        assert response.status_code == 200
        assert "id" in response.json()
        global sess_id
        sess_id = response.json()["id"]


@pytest.mark.asyncio
async def test_fetch_session():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/session/" + sess_id)
    assert response.status_code == 200
    assert sess_id in response.json()["session"]["_id"]


@pytest.mark.asyncio
async def test_fetch_sessions():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/session/all")
    assert response.status_code == 200
    assert sess_id in response.json()["sessions"][0]["_id"]


@pytest.mark.asyncio
async def test_delete_session():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.delete("/session/delete/" + sess_id)
    assert response.status_code == 200
    assert response.json() == {"msg": "Session deleted."}
