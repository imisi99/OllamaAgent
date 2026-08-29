from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

proj_details = {}


def test_get_projects_empty():
    response = client.get("/project/all")

    assert response.status_code == 404


def test_create_project():
    response = client.post(
        url="/project/create", json={"name": "Test Project", "goal": "Test Project"}
    )

    assert response.status_code == 201 and "id" in response.json()
    proj_details["id"] = response.json()["id"]


def test_edit_project():
    response = client.put(
        url=f"/project/edit/{proj_details["id"]}",
        json={
            "name": "Test Project",
            "goal": "Test Project",
        },
    )

    assert response.status_code == 202


def test_get_projects():
    response = client.get("/project/all")

    assert response.status_code == 200 and "projects" in response.json()

    proj = response.json()["projects"][0]
    proj_details[proj["_id"]] = proj


def test_get_project():
    response = client.get(f"/project/{proj_details["id"]}")

    assert response.status_code == 200
    assert "project" in response.json() and "sessions" in response.json()


def test_fetch_project_exclude():
    response = client.get(f"/project/all/exclude/{proj_details["id"]}")

    assert response.status_code == 404


def test_create_sess_to_add():
    response = client.post(
        url="/session/create",
        json={
            "prompt": "Testing the create session endpoint",
            "audio": None,
            "files": [],
            "images": [],
        },
    )

    assert response.status_code == 201 and "id" in response.json()
    proj_details["sess_id"] = response.json()["id"]
    proj_details["sess_uid"] = response.json()["uid"]


def test_add_to_project():
    response = client.put(
        f"/project/add/{proj_details["id"]}",
        json={
            "ids": [proj_details["sess_id"]],
        },
    )

    assert response.status_code == 202


def test_get_project_session():
    response = client.get(f"/project/{proj_details["id"]}")

    assert response.status_code == 200
    assert "project" in response.json() and "sessions" in response.json()
    assert len(response.json()["sessions"]) == 1


def test_rem_from_project():
    response = client.put(
        f"/project/remove/{proj_details["id"]}",
        json={
            "ids": [proj_details["sess_id"]],
        },
    )

    assert response.status_code == 202


def test_get_project_session_rem():
    response = client.get(f"/project/{proj_details["id"]}")

    assert response.status_code == 200
    assert "project" in response.json() and "sessions" in response.json()
    assert len(response.json()["sessions"]) == 0


def test_delete_project():
    response = client.delete(f"/project/delete/{proj_details["id"]}")

    assert response.status_code == 204


def test_delete_session_project():
    response = client.delete(
        url="/session/delete/"
        + proj_details["sess_id"]
        + "/"
        + proj_details["sess_uid"],
    )

    assert response.status_code == 204
