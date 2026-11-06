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
