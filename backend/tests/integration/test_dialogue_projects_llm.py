"""Real projects/auth/storage, with offline HTTP for both LLM adapters."""

import json
import uuid

import httpx
import pytest


@pytest.mark.parametrize("provider", ["ollama", "cloudflare"])
def test_moving_chat_keeps_history_and_separate_model_context(
    client, monkeypatch, provider,
):
    requests = []
    original_client = httpx.AsyncClient
    monkeypatch.setenv("LLM_PROVIDER", provider)
    monkeypatch.setenv("LLM_BASE_URL", "http://127.0.0.1:11434")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "a" * 32)
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "synthetic-test-token")

    def handler(request):
        body = json.loads(request.content)
        requests.append(body)
        if len(requests) == 4:
            return httpx.Response(429, json={"success": False})
        content = body["messages"][-1]["content"]
        generated = {
            "reply": "Recorded synthetic reply.",
            "corrected_text": content.replace("I is here", "I am here"),
        }
        if provider == "cloudflare":
            assert request.url.host == "api.cloudflare.com"
            payload = {"success": True, "result": {"response": generated}}
        else:
            assert request.url.host == "127.0.0.1"
            payload = {"done": True, "message": {
                "role": "assistant", "content": json.dumps(generated),
            }}
        return httpx.Response(200, json=payload)

    def offline_client(**kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return original_client(**kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", offline_client)
    email = f"synthetic-project-ai-{uuid.uuid4().hex}@example.com"
    assert client.post("/api/v1/auth/register", json={
        "name": "Synthetic learner", "email": email,
        "password": "synthetic-test-password",
    }).status_code == 201
    login = client.post("/api/v1/auth/login", json={
        "email": email, "password": "synthetic-test-password",
    })
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    def create(path, data):
        response = client.post(f"/api/v1/{path}", headers=headers, json=data)
        assert response.status_code == 201
        return response.json()

    project = create("projects", {"name": "First folder"})
    target = create("projects", {"name": "UNTRUSTED_FOLDER_NAME"})
    first = create("dialogues", {
        "scenario": "cafe", "project_id": project["id"],
    })
    second = create("dialogues", {
        "scenario": "shop", "project_id": project["id"],
    })
    first_url = f"/api/v1/dialogues/{first['id']}/messages"
    second_url = f"/api/v1/dialogues/{second['id']}/messages"
    pair = client.post(first_url, headers=headers, json={
        "content": "FIRST_ONLY I is here.",
    })
    assert pair.status_code == 201
    assert pair.json()["user_message"]["correction"]
    history = client.get(first_url, headers=headers).json()
    other = client.post(second_url, headers=headers, json={
        "content": "SECOND_ONLY Hello.",
    })
    assert other.status_code == 201
    assert "FIRST_ONLY" not in json.dumps(requests[1])
    moved = client.patch(
        f"/api/v1/dialogues/{first['id']}/project", headers=headers,
        json={"project_id": target["id"]},
    )
    assert moved.status_code == 200
    assert moved.json()["project_id"] == target["id"]
    assert moved.json()["scenario"] == "cafe"
    assert client.get(first_url, headers=headers).json() == history
    again = client.post(first_url, headers=headers, json={
        "content": "NEXT_FIRST Hello again.",
    })
    assert again.status_code == 201
    messages = requests[2]["messages"]
    assert messages[0] == requests[0]["messages"][0]
    assert [item["content"] for item in messages[1:]] == [
        history[0]["content"], history[1]["content"],
        "NEXT_FIRST Hello again.",
    ]
    assert "SECOND_ONLY" not in json.dumps(requests[2])
    assert "UNTRUSTED_FOLDER_NAME" not in json.dumps(requests[2])
    saved = client.get(first_url, headers=headers).json()
    failed = client.post(first_url, headers=headers, json={
        "content": "This synthetic turn must not persist.",
    })
    assert failed.status_code == 503
    assert failed.json()["error"]["code"] == "service_unavailable"
    assert client.get(first_url, headers=headers).json() == saved
