"""Real API and storage with synthetic users and offline Cloudflare HTTP."""

import json
import uuid

import httpx
import pytest


@pytest.fixture()
def cloud_transport(monkeypatch):
    requests = []
    response = {
        "status": 200,
        "body": {
            "success": True,
            "result": {"response": {
                "reply": "Hello! What would you like?",
                "corrected_text": "I am hungry.",
            }},
        },
    }
    original_client = httpx.AsyncClient

    def handler(request):
        requests.append(request)
        return httpx.Response(response["status"], json=response["body"])

    def offline_client(**kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return original_client(**kwargs)

    monkeypatch.setenv("LLM_PROVIDER", "cloudflare")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "a" * 32)
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "synthetic-test-token")
    monkeypatch.setattr(httpx, "AsyncClient", offline_client)
    return requests, response


def sign_in(client):
    email = f"synthetic-cloud-{uuid.uuid4().hex}@example.com"
    registered = client.post("/api/v1/auth/register", json={
        "name": "Synthetic learner", "email": email,
        "password": "synthetic-test-password",
    })
    assert registered.status_code == 201
    login = client.post("/api/v1/auth/login", json={
        "email": email, "password": "synthetic-test-password",
    })
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def create_dialogue(client, headers, scenario="cafe"):
    response = client.post("/api/v1/dialogues", headers=headers, json={
        "scenario": scenario,
    })
    assert response.status_code == 201
    return response.json()


@pytest.mark.parametrize("scenario", ["introductions", "cafe", "shop"])
def test_selected_cloud_provider_preserves_pair_and_history(
    client, cloud_transport, scenario,
):
    requests, _ = cloud_transport
    headers = sign_in(client)
    dialogue = create_dialogue(client, headers, scenario)
    url = f"/api/v1/dialogues/{dialogue['id']}/messages"
    pair = client.post(url, headers=headers, json={"content": "I is hungry."})
    assert pair.status_code == 201
    user = pair.json()["user_message"]
    assert 'Заменено "is" на "am".' in user["correction"]
    assistant = pair.json()["assistant_message"]
    assert assistant["content"] == "Hello! What would you like?"
    assert client.get(url, headers=headers).json() == [user, assistant]
    again = client.post(url, headers=headers, json={"content": "I is hungry."})
    assert again.status_code == 201
    assert len(requests) == 2
    assert requests[0].url.host == "api.cloudflare.com"
    body = json.loads(requests[1].content)
    assert [m["role"] for m in body["messages"]] == [
        "system", "user", "assistant", "user",
    ]
    assert "Trusted learner CEFR: A1" in body["messages"][0]["content"]
    assert "synthetic-test-password" not in requests[1].content.decode()
    assert "@example.com" not in requests[1].content.decode()


@pytest.mark.parametrize("status,payload,want", [
    (429, {"errors": [{"code": 3036}]}, 503),
    (403, {"errors": [{"code": 5035}]}, 503),
    (200, {"success": False, "errors": [{"code": 3036}]}, 503),
    (200, {"success": True, "result": {"response": "invalid JSON"}}, 502),
])
def test_cloud_error_preserves_existing_history_and_updated_time(
    client, cloud_transport, status, payload, want,
):
    requests, response = cloud_transport
    headers = sign_in(client)
    dialogue = create_dialogue(client, headers)
    url = f"/api/v1/dialogues/{dialogue['id']}/messages"
    assert client.post(
        url, headers=headers, json={"content": "I is hungry."}
    ).status_code == 201
    history = client.get(url, headers=headers).json()
    before = client.get("/api/v1/dialogues", headers=headers).json()
    response.update(status=status, body=payload)
    failed = client.post(url, headers=headers, json={"content": "Hello!"})
    assert failed.status_code == want
    assert "synthetic-test-token" not in failed.text
    assert len(requests) == 2
    assert client.get(url, headers=headers).json() == history
    assert client.get("/api/v1/dialogues", headers=headers).json() == before


def test_foreign_dialogue_never_reaches_cloudflare(client, cloud_transport):
    requests, _ = cloud_transport
    owner = sign_in(client)
    other = sign_in(client)
    dialogue = create_dialogue(client, owner)
    url = f"/api/v1/dialogues/{dialogue['id']}/messages"
    assert client.post(
        url, headers=other, json={"content": "Hello!"}
    ).status_code == 404
    assert requests == []


def test_missing_cloud_credentials_returns_503_without_http(
    client, cloud_transport, monkeypatch,
):
    requests, _ = cloud_transport
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "")
    headers = sign_in(client)
    dialogue = create_dialogue(client, headers)
    url = f"/api/v1/dialogues/{dialogue['id']}/messages"
    failed = client.post(url, headers=headers, json={"content": "Hello!"})
    assert failed.status_code == 503
    assert client.get(url, headers=headers).json() == []
    assert requests == []
