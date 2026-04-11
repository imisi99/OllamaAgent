from typing import Any
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

user: dict[str, Any] = {}


def test_get_user():
    response = client.get(url="/user")

    assert response.status_code == 404


def test_create_user():
    response = client.post(url="/user/create/" + "Imisioluwa23")

    assert response.status_code == 201
    assert "id" in response.json()

    user["id"] = response.json()["id"]


def test_get_user_id():
    response = client.get(url="/user/me/" + user["id"])

    assert response.status_code == 200
    assert "user" in response.json()


def test_get_user_id_fail():
    response = client.get(url="/user/me/FakeID")

    assert response.status_code == 404


def test_update_memory():
    response = client.put(
        url="/user/" + user["id"] + "/update/memory",
        json={"key": "SomeStuff", "value": "SomeDetails"},
    )

    assert response.status_code == 202


def test_update_username():
    response = client.put(url="/user/" + user["id"] + "/update/" + "Imisioluwa")

    assert response.status_code == 202
    user["name"] = "Imisioluwa"


def test_get_user_updates():
    response = client.get(url="/user/me/" + user["id"])

    assert response.status_code == 200
    assert "user" in response.json()
    assert "memory" in response.json()["user"]

    memory = response.json()["user"]["memory"]

    assert (
        len(memory) == 1
        and "SomeStuff" in memory
        and "SomeDetails" == memory["SomeStuff"]
        and user["name"] == response.json()["user"]["name"]
    )


def test_delete_memory():
    response = client.delete("/user/" + user["id"] + "/delete/memory/SomeStuff")

    assert response.status_code == 202


def test_delete_memory_fail():
    response = client.delete("/user/" + user["id"] + "/delete/memory/SomeStuff")

    assert response.status_code == 500


def test_get_user_memory():
    response = client.get(url="/user/me/" + user["id"])

    assert response.status_code == 200
    assert "user" in response.json()
    assert "memory" in response.json()["user"]

    memory = response.json()["user"]["memory"]

    assert len(memory) == 0
