from datetime import datetime
from fastapi.testclient import TestClient


from main import app

client = TestClient(app)

sess_details: dict[str, str] = {}


def test_fetch_all_session_preview_empty():
    response = client.get(url="/session/all/preview")

    assert response.status_code == 404


def test_create_session():
    response = client.post(
        url="/session/create",
        json={
            "prompt": "Testing the create session endpoint",
            "audio": None,
            "files": [],
            "images": [],
        },
    )
    assert (
        response.status_code == 201
        and "id" in response.json()
        and "uid" in response.json()
    )

    sess_details["_id"] = response.json()["id"]
    sess_details["uuid"] = response.json()["uid"]


def test_rename_session():
    response = client.put(
        url=f"/session/rename/{sess_details["_id"]}/{sess_details["uuid"]}?name=Knightmares"
    )

    assert response.status_code == 202


def test_new_session_name():
    response = client.get(url="/session/" + sess_details["_id"])

    assert response.status_code == 200
    assert "session" in response.json()

    session = response.json()["session"]
    assert session["name"] == "Knightmares"


def test_create_message():
    response = client.put(
        url=f"/session/msg/{sess_details["_id"]}/{sess_details["uuid"]}",
        json={
            "role": "test",
            "content": "Testing the add message endpoint",
            "audio": None,
            "thought": "",
            "files": [],
            "images": [],
            "session_id": "",
            "timestamp": datetime.now().isoformat(),
        },
    )

    assert response.status_code == 202


def test_fetch_all_session_preview():
    response = client.get(url="/session/all/preview")

    assert response.status_code == 200
    assert "sessions" in response.json()

    session = response.json()["sessions"][0]
    assert (
        session["_id"] == sess_details["_id"]
        and session["uuid"] == sess_details["uuid"]
    )


def test_fetch_all_session():
    response = client.get(url="/session/all")

    assert response.status_code == 200
    assert "sessions" in response.json()

    session = response.json()["sessions"][0]
    sess, msg = session[0], session[1]
    assert sess["_id"] == sess_details["_id"] and sess["uuid"] == sess_details["uuid"]
    assert len(msg) == 2


def test_fetch_session():
    response = client.get(url="/session/" + sess_details["_id"])

    assert response.status_code == 200
    assert "session" in response.json()

    session = response.json()["session"]
    messages = response.json()["messages"]

    assert (
        session["_id"] == sess_details["_id"]
        and session["uuid"] == sess_details["uuid"]
        and len(messages) == 2
    )


def test_delete_session():
    response = client.delete(
        url="/session/delete/" + sess_details["_id"] + "/" + sess_details["uuid"],
    )

    assert response.status_code == 204
