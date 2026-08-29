from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_chat_agent():
    response = client.post(
        url="/agent/chat",
        json={
            "user_id": "stuff",
            "session_id": "stuff",
            "session_uid": "stuff",
            "message": {
                "role": "stuff",
                "content": "stuff",
                "thought": "",
                "audio": None,
                "session_id": "",
                "timestamp": "stuff",
                "files": [],
                "images": [],
            },
            "ghost_session": True,
        },
    )

    assert response.status_code == 200 and "msg" in response.json()
