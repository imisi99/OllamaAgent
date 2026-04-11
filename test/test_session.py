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
        url="/session/create", json={"prompt": "Testing the create session endpoint"}
    )
    assert response.status_code == 201
    assert "id" in response.json()
    assert "uid" in response.json()

    sess_details["_id"] = response.json()["id"]
    sess_details["uuid"] = response.json()["uid"]


def test_rename_session():
    response = client.put(
        url="/session/rename/"
        + sess_details["_id"]
        + "/"
        + sess_details["uuid"]
        + "?name="
        + "The new name of the session",
    )

    assert response.status_code == 202


def test_new_session_name():
    response = client.get(url="/session/" + sess_details["_id"])

    assert response.status_code == 200
    assert "session" in response.json()

    session = response.json()["session"]
    assert session["name"] == "The new name of the session"


def test_rename_session_fail():
    response = client.put(
        url="/session/rename/"
        + "This should fail"
        + "/"
        + sess_details["uuid"]
        + "?name="
        + "This should fail",
    )

    assert response.status_code == 500


def test_add_message():
    response = client.put(
        url="/session/msg/" + sess_details["_id"] + "/" + sess_details["uuid"],
        json={
            "role": "test",
            "content": "Testing the add message endpoint",
            "timestamp": datetime.now().isoformat(),
        },
    )

    assert response.status_code == 202


def test_fetch_session():
    response = client.get(url="/session/" + sess_details["_id"])

    assert response.status_code == 200
    assert "session" in response.json()

    session = response.json()["session"]
    messages = response.json()["session"]["messages"]

    assert (
        session["_id"] == sess_details["_id"]
        and session["uuid"] == sess_details["uuid"]
        and len(messages) == 1
        and "Testing the add message endpoint" in messages[0]["content"]
    )


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
    assert (
        session["_id"] == sess_details["_id"]
        and session["uuid"] == sess_details["uuid"]
    )


def test_fetch_session_fail():
    response = client.get(url="/session/" + "WrongID")

    assert response.status_code == 404


def test_delete_session():
    response = client.delete(
        url="/session/delete/" + sess_details["_id"] + "/" + sess_details["uuid"],
    )

    assert response.status_code == 200


def test_delete_session_fail():
    response = client.delete(
        url="/session/delete/" + sess_details["_id"] + "/" + sess_details["uuid"],
    )

    assert response.status_code == 500
