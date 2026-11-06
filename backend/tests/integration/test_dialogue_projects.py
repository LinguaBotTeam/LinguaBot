"""Project API checks use real storage and synthetic users only."""

from datetime import datetime
import uuid

import pytest


PROJECTS = "/api/v1/projects"
DIALOGUES = "/api/v1/dialogues"


def sign_in(client):
    email = f"project-{uuid.uuid4().hex}@example.com"
    payload = {
        "name": "Synthetic learner", "email": email,
        "password": "synthetic-test-password",
    }
    registered = client.post("/api/v1/auth/register", json=payload)
    assert registered.status_code == 201
    login = client.post("/api/v1/auth/login", json={
        "email": email, "password": payload["password"],
    })
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def create_project(client, headers, name="Synthetic trip"):
    response = client.post(PROJECTS, headers=headers, json={"name": name})
    assert response.status_code == 201
    return response.json()


def test_projects_require_authentication(client):
    assert client.get(PROJECTS).status_code == 401
    assert client.post(PROJECTS, json={"name": "Trip"}).status_code == 401


def test_create_project_persists_and_normalizes_name(client):
    owner = sign_in(client)
    assert client.get(PROJECTS, headers=owner).json() == []
    project = create_project(client, owner, "  Synthetic trip  ")
    assert set(project) == {"id", "name", "created_at"}
    assert project["id"] > 0
    assert project["name"] == "Synthetic trip"
    datetime.fromisoformat(project["created_at"])
    assert client.get(PROJECTS, headers=owner).json() == [project]


def test_projects_are_owner_scoped_ordered_and_paginated(client):
    owner, other = sign_in(client), sign_in(client)
    first = create_project(client, owner, "First")
    foreign = create_project(client, other, "Foreign")
    second = create_project(client, owner, "Second")
    assert client.get(PROJECTS, headers=owner).json() == [second, first]
    assert client.get(PROJECTS, headers=other).json() == [foreign]
    page = client.get(PROJECTS, headers=owner,
                      params={"limit": 1, "offset": 1})
    assert page.json() == [first]
    assert client.get(PROJECTS, headers=owner,
                      params={"offset": 2}).json() == []


def test_same_project_names_are_allowed(client):
    owner = sign_in(client)
    first = create_project(client, owner)
    second = create_project(client, owner)
    assert first["id"] != second["id"]
    assert first["name"] == second["name"]


@pytest.mark.parametrize("payload", [
    {}, {"name": ""}, {"name": "   "}, {"name": "x" * 161},
    {"name": "Trip", "user_id": 999},
])
def test_invalid_project_requests_are_rejected(client, payload):
    owner = sign_in(client)
    response = client.post(PROJECTS, headers=owner, json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert client.get(PROJECTS, headers=owner).json() == []


@pytest.mark.parametrize("params", [
    {"limit": 0}, {"limit": 101}, {"offset": -1}, {"limit": "bad"},
])
def test_invalid_project_pagination_is_rejected(client, params):
    owner = sign_in(client)
    response = client.get(PROJECTS, headers=owner, params=params)
    assert response.status_code == 422


def create_dialogue(client, headers, **payload):
    response = client.post(DIALOGUES, headers=headers, json=payload)
    assert response.status_code == 201
    return response.json()


def test_dialogue_filters_preserve_default_list_and_pagination(client):
    owner, other = sign_in(client), sign_in(client)
    first = create_project(client, owner)
    second = create_project(client, owner)
    empty = create_project(client, owner)
    foreign = create_project(client, other)
    plain = create_dialogue(client, owner)
    one = create_dialogue(client, owner, project_id=first["id"])
    two = create_dialogue(client, owner, project_id=second["id"])
    latest = create_dialogue(client, owner, project_id=first["id"])
    create_dialogue(client, other, project_id=foreign["id"])
    assert plain["project_id"] is None
    assert one["project_id"] == first["id"]
    assert client.get(DIALOGUES, headers=owner).json() == [
        latest, two, one, plain,
    ]
    for params, expected in [
        ({"project_id": first["id"]}, [latest, one]),
        ({"project_id": first["id"], "limit": 1, "offset": 1}, [one]),
        ({"project_id": empty["id"]}, []),
        ({"unassigned": True}, [plain]),
        ({"unassigned": True, "offset": 1}, []),
        ({"unassigned": False}, [latest, two, one, plain]),
    ]:
        response = client.get(DIALOGUES, headers=owner, params=params)
        assert response.status_code == 200
        assert response.json() == expected
    for project_id in (foreign["id"], 2147483647):
        response = client.get(
            DIALOGUES, headers=owner, params={"project_id": project_id}
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"


def test_move_dialogue_preserves_content_and_allows_detach(client):
    owner = sign_in(client)
    first, second = create_project(
        client, owner), create_project(client, owner)
    dialogue = create_dialogue(client, owner, title="Airport", scenario="cafe")
    history_url = f"{DIALOGUES}/{dialogue['id']}/messages"
    # Empty history is also preserved; populated/corrected history is tested
    # with real storage in the service test, without invoking any LLM.
    history = client.get(history_url, headers=owner).json()
    url = f"{DIALOGUES}/{dialogue['id']}/project"
    for project_id in (first["id"], first["id"], second["id"], None):
        response = client.patch(
            url, headers=owner, json={"project_id": project_id}
        )
        assert response.status_code == 200
        moved = response.json()
        assert moved["project_id"] == project_id
        for key in ("id", "title", "scenario", "status", "created_at"):
            assert moved[key] == dialogue[key]
        assert client.get(history_url, headers=owner).json() == history
        assert client.get(DIALOGUES, headers=owner).json() == [moved]


def test_foreign_targets_are_hidden_and_never_change_assignment(client):
    owner, other = sign_in(client), sign_in(client)
    own_project = create_project(client, owner)
    foreign_project = create_project(client, other)
    own = create_dialogue(client, owner, project_id=own_project["id"])
    foreign = create_dialogue(client, other)
    responses = []
    for project_id in (foreign_project["id"], 2147483647):
        response = client.post(
            DIALOGUES, headers=owner, json={"project_id": project_id}
        )
        assert response.status_code == 404
        responses.append(response.json())
        moved = client.patch(
            f"{DIALOGUES}/{own['id']}/project", headers=owner,
            json={"project_id": project_id},
        )
        assert moved.status_code == 404
        assert moved.json() == response.json()
    assert responses[0] == responses[1]
    foreign_errors = []
    for dialogue_id in (foreign["id"], 2147483647):
        response = client.patch(
            f"{DIALOGUES}/{dialogue_id}/project", headers=owner,
            json={"project_id": own_project["id"]},
        )
        assert response.status_code == 404
        foreign_errors.append(response.json())
    assert foreign_errors[0] == foreign_errors[1]
    assert client.get(DIALOGUES, headers=owner).json() == [own]
    assert client.get(DIALOGUES, headers=other).json() == [foreign]


def test_invalid_assignment_and_filter_requests_never_write(client):
    owner = sign_in(client)
    dialogue = create_dialogue(client, owner)
    url = f"{DIALOGUES}/{dialogue['id']}/project"
    assert client.patch(url, json={"project_id": None}).status_code == 401
    for payload in ({}, {"project_id": 0}, {"project_id": 2147483648},
                    {"project_id": None, "user_id": 123}):
        response = client.patch(url, headers=owner, json=payload)
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"
    for params in ({"project_id": 0}, {"project_id": 2147483648},
                   {"project_id": 1, "unassigned": True}):
        response = client.get(DIALOGUES, headers=owner, params=params)
        assert response.status_code == 422
    assert client.get(DIALOGUES, headers=owner).json() == [dialogue]
