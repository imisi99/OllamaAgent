from fastapi.testclient import TestClient
from main import app


client = TestClient(app)


def test_chat_agent():
    response = client.post(
        url="/agent/chat",
        json={
            "user_id": "stuff",
            "session_id": "stuff",
            "message": {"role": "stuff", "content": "stuff", "timestamp": "stuff"},
            "ghost_session": True,
        },
    )

    assert "msg" in response.json()
