"""Chat API contracts exercised with real authentication and persisted history."""

from datetime import datetime, timedelta, timezone
import uuid

import jwt
import pytest
from fastapi.testclient import TestClient

from linguabot.core.config import settings

DIALOGUES = "/api/v1/dialogues"


@pytest.fixture(autouse=True)
def offline_model(monkeypatch):
    """Only the external inference boundary is replaced; all API/storage stays real."""
    from linguabot.integrations.llm import ModelReply
    from linguabot.modules.dialogues import service

    class DeterministicModel:
        async def generate(self, messages):
            return ModelReply(reply="Hello! Let us practice.", correction=None)

    monkeypatch.setattr(service, "get_language_model", lambda: DeterministicModel())


def sign_in(client):
    email = f"chat-{uuid.uuid4().hex}@example.com"
    registration = client.post(
        "/api/v1/auth/register",
        json={"name": "Chat tester", "email": email, "password": "secret123"},
    )
    assert registration.status_code == 201
    login = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "secret123"}
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}, registration.json()


def create_dialogue(client, headers, **payload):
    response = client.post(DIALOGUES, headers=headers, json=payload)
    assert response.status_code == 201
    return response.json()


def messages_url(dialogue):
    return f"{DIALOGUES}/{dialogue['id']}/messages"


def assert_error(response, status, code, field=None):
    assert response.status_code == status
    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message", "field"}
    assert body["error"]["code"] == code
    assert isinstance(body["error"]["message"], str) and body["error"]["message"]
    assert body["error"]["field"] == field


def assert_message(message, dialogue_id, role, content=None):
    assert set(message) == {"id", "dialogue_id", "role", "content", "correction", "created_at"}
    assert isinstance(message["id"], int) and message["id"] > 0
    assert message["dialogue_id"] == dialogue_id
    assert message["role"] == role
    assert message["correction"] is None
    assert isinstance(message["content"], str) and message["content"].strip()
    if content is not None:
        assert message["content"] == content
    datetime.fromisoformat(message["created_at"])


@pytest.mark.parametrize(
    ("payload", "title", "scenario"),
    [({}, "Новый диалог", "free_chat"), ({"title": "Travel", "scenario": "travel"}, "Travel", "travel")],
)
def test_create_dialogue_returns_contract_and_persists(client, payload, title, scenario):
    headers, _ = sign_in(client)
    assert client.get(DIALOGUES, headers=headers).json() == []

    dialogue = create_dialogue(client, headers, **payload)

    assert set(dialogue) == {"id", "title", "scenario", "status", "created_at", "updated_at"}
    assert isinstance(dialogue["id"], int) and dialogue["id"] > 0
    assert dialogue["title"] == title
    assert dialogue["scenario"] == scenario
    assert dialogue["status"] == "active"
    assert datetime.fromisoformat(dialogue["updated_at"]) >= datetime.fromisoformat(dialogue["created_at"])
    listing = client.get(DIALOGUES, headers=headers)
    assert listing.status_code == 200
    assert listing.json() == [dialogue]


def test_dialogue_list_is_owner_scoped_newest_first_and_paginated(client):
    owner, _ = sign_in(client)
    other, _ = sign_in(client)
    first = create_dialogue(client, owner, title="First")
    foreign = create_dialogue(client, other, title="Other user's dialogue")
    second = create_dialogue(client, owner, title="Second")
    third = create_dialogue(client, owner, title="Third")

    listing = client.get(DIALOGUES, headers=owner)
    assert listing.status_code == 200
    assert listing.json() == [third, second, first]
    assert client.get(DIALOGUES, headers=other).json() == [foreign]
    assert client.get(DIALOGUES, headers=owner, params={"limit": 1, "offset": 1}).json() == [second]
    assert client.get(DIALOGUES, headers=owner, params={"offset": 3}).json() == []
    assert client.get(DIALOGUES, headers=owner, params={"limit": 100, "offset": 0}).status_code == 200


def test_dialogue_owner_cannot_be_supplied_by_client(client):
    headers, _ = sign_in(client)
    _, other_user = sign_in(client)
    response = client.post(DIALOGUES, headers=headers, json={"user_id": other_user["id"]})

    assert_error(response, 422, "validation_error", "user_id")
    assert client.get(DIALOGUES, headers=headers).json() == []


def test_message_pair_is_trimmed_persisted_and_ordered_with_deterministic_model(client):
    headers, _ = sign_in(client)
    dialogue = create_dialogue(client, headers)
    url = messages_url(dialogue)
    empty = client.get(url, headers=headers)
    assert empty.status_code == 200
    assert empty.json() == []

    first = client.post(url, headers=headers, json={"content": " \n Hello there! \t "})
    assert first.status_code == 201
    first_pair = first.json()
    assert set(first_pair) == {"user_message", "assistant_message"}
    assert_message(first_pair["user_message"], dialogue["id"], "user", "Hello there!")
    assert_message(first_pair["assistant_message"], dialogue["id"], "assistant")
    expected_first = [first_pair["user_message"], first_pair["assistant_message"]]
    assert expected_first[0]["id"] < expected_first[1]["id"]
    assert client.get(url, headers=headers).json() == expected_first

    second = client.post(url, headers=headers, json={"content": "A different question"})
    assert second.status_code == 201
    second_pair = second.json()
    assert_message(second_pair["user_message"], dialogue["id"], "user", "A different question")
    assert_message(second_pair["assistant_message"], dialogue["id"], "assistant")
    assert second_pair["assistant_message"]["content"] == first_pair["assistant_message"]["content"]
    expected = expected_first + [second_pair["user_message"], second_pair["assistant_message"]]
    assert len({message["id"] for message in expected}) == 4
    assert [message["id"] for message in expected] == sorted(message["id"] for message in expected)
    history = client.get(url, headers=headers)
    assert history.status_code == 200
    assert history.json() == expected
    assert client.get(url, headers=headers, params={"limit": 2, "offset": 1}).json() == expected[1:3]
    assert client.get(url, headers=headers, params={"offset": 4}).json() == []
    assert client.get(url, headers=headers, params={"limit": 100, "offset": 0}).json() == expected


def test_history_remains_available_in_a_new_client_context(client):
    headers, _ = sign_in(client)
    dialogue = create_dialogue(client, headers, title="Persistent dialogue")
    url = messages_url(dialogue)
    sent = client.post(url, headers=headers, json={"content": "Remember this message"})
    assert sent.status_code == 201
    expected = [sent.json()["user_message"], sent.json()["assistant_message"]]

    with TestClient(client.app) as reopened:
        listing = reopened.get(DIALOGUES, headers=headers)
        assert listing.status_code == 200
        assert [item["id"] for item in listing.json()] == [dialogue["id"]]
        history = reopened.get(url, headers=headers)
        assert history.status_code == 200
        assert history.json() == expected


def test_foreign_and_missing_dialogues_are_indistinguishable_and_never_written(client):
    owner, _ = sign_in(client)
    other, _ = sign_in(client)
    dialogue = create_dialogue(client, owner)
    url = messages_url(dialogue)
    missing_url = f"{DIALOGUES}/2147483647/messages"
    sent = client.post(url, headers=owner, json={"content": "Owner's message"})
    assert sent.status_code == 201
    original_history = client.get(url, headers=owner).json()

    for method in ("get", "post"):
        kwargs = {"json": {"content": "Unauthorized write"}} if method == "post" else {}
        foreign = client.request(method, url, headers=other, **kwargs)
        missing = client.request(method, missing_url, headers=other, **kwargs)
        assert_error(foreign, 404, "not_found")
        assert_error(missing, 404, "not_found")
        assert foreign.json() == missing.json()

    assert client.get(url, headers=owner).json() == original_history
    assert client.get(DIALOGUES, headers=other).json() == []


@pytest.mark.parametrize(("method", "resource"), [("get", "dialogues"), ("post", "dialogues"), ("get", "messages"), ("post", "messages")])
def test_every_chat_operation_rejects_missing_invalid_and_expired_tokens(client, method, resource):
    headers, user = sign_in(client)
    dialogue = create_dialogue(client, headers)
    url = DIALOGUES if resource == "dialogues" else messages_url(dialogue)
    now = datetime.now(timezone.utc)
    expired = jwt.encode(
        {"sub": str(user["id"]), "iat": now - timedelta(hours=1), "exp": now - timedelta(seconds=1)},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    kwargs = {"json": {"content": "Hello"} if resource == "messages" else {}} if method == "post" else {}
    for token_headers in ({}, {"Authorization": "Bearer not-a-token"}, {"Authorization": f"Bearer {expired}"}):
        response = client.request(method, url, headers=token_headers, **kwargs)
        assert_error(response, 401, "unauthorized")


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({}, "content"),
        ({"content": ""}, "content"),
        ({"content": " \n\t "}, "content"),
        ({"content": "x" * 4001}, "content"),
        ({"content": "Hello", "role": "assistant"}, "role"),
        ({"content": "Hello", "dialogue_id": 1}, "dialogue_id"),
    ],
)
def test_invalid_messages_are_rejected_without_persisting_any_message(client, payload, field):
    headers, _ = sign_in(client)
    url = messages_url(create_dialogue(client, headers))

    response = client.post(url, headers=headers, json=payload)

    assert_error(response, 422, "validation_error", field)
    assert client.get(url, headers=headers).json() == []


def test_message_at_length_limit_is_accepted_and_persisted(client):
    headers, _ = sign_in(client)
    url = messages_url(create_dialogue(client, headers))
    content = "x" * 4000
    response = client.post(url, headers=headers, json={"content": content})

    assert response.status_code == 201
    assert response.json()["user_message"]["content"] == content
    assert client.get(url, headers=headers).json()[0]["content"] == content


def test_message_history_is_scoped_to_the_selected_dialogue(client):
    headers, _ = sign_in(client)
    first_url = messages_url(create_dialogue(client, headers))
    second_url = messages_url(create_dialogue(client, headers))
    sent = client.post(first_url, headers=headers, json={"content": "Only in the first dialogue"})
    assert sent.status_code == 201

    assert client.get(second_url, headers=headers).json() == []
    assert len(client.get(first_url, headers=headers).json()) == 2


@pytest.mark.parametrize("method", ["get", "post"])
def test_oversized_dialogue_id_is_rejected_before_database_access(client, method):
    headers, _ = sign_in(client)
    url = f"{DIALOGUES}/2147483648/messages"
    kwargs = {"json": {"content": "Hello"}} if method == "post" else {}

    response = client.request(method, url, headers=headers, **kwargs)

    assert_error(response, 422, "validation_error", "dialogue_id")


@pytest.mark.parametrize("resource", ["dialogues", "messages"])
def test_default_page_contains_at_most_100_records(client, resource):
    headers, _ = sign_in(client)
    if resource == "dialogues":
        created = [create_dialogue(client, headers) for _ in range(101)]
        url = DIALOGUES
        expected = list(reversed(created))[:100]
    else:
        url = messages_url(create_dialogue(client, headers))
        created = []
        for _ in range(51):
            response = client.post(url, headers=headers, json={"content": "Hello"})
            assert response.status_code == 201
            pair = response.json()
            created.extend([pair["user_message"], pair["assistant_message"]])
        expected = created[:100]

    response = client.get(url, headers=headers)
    assert response.status_code == 200
    assert response.json() == expected


@pytest.mark.parametrize("resource", ["dialogues", "messages"])
@pytest.mark.parametrize(("params", "field"), [({"limit": 0}, "limit"), ({"limit": 101}, "limit"), ({"offset": -1}, "offset")])
def test_pagination_bounds_are_validated(client, resource, params, field):
    headers, _ = sign_in(client)
    url = DIALOGUES if resource == "dialogues" else messages_url(create_dialogue(client, headers))

    response = client.get(url, headers=headers, params=params)

    assert_error(response, 422, "validation_error", field)


@pytest.mark.parametrize("kind,status,code", [
    ("unavailable", 503, "service_unavailable"), ("invalid", 502, "bad_gateway"),
    ("settings", 503, "service_unavailable"),
])
def test_model_failure_returns_sanitized_api_error_without_changing_dialogue(client, monkeypatch, kind, status, code):
    from linguabot.integrations.llm import LLMInvalidResponseError, LLMUnavailableError, LLMSettings
    from linguabot.modules.dialogues import service

    class FailingModel:
        async def generate(self, messages):
            raise LLMUnavailableError() if kind == "unavailable" else LLMInvalidResponseError()

    if kind == "settings":
        monkeypatch.setattr(service, "get_language_model", lambda: LLMSettings(_env_file=None, base_url="https://example.com/private-detail"))
    else:
        monkeypatch.setattr(service, "get_language_model", lambda: FailingModel())
    headers, _ = sign_in(client)
    dialogue = create_dialogue(client, headers)
    url = messages_url(dialogue)

    response = client.post(url, headers=headers, json={"content": "Hello!"})

    assert_error(response, status, code)
    assert "private-detail" not in response.text
    assert client.get(url, headers=headers).json() == []
    assert client.get(DIALOGUES, headers=headers).json() == [dialogue]


def test_correction_is_returned_and_persisted_on_user_message_only(client, monkeypatch):
    from linguabot.integrations.llm import ModelReply
    from linguabot.modules.dialogues import service

    class CorrectingModel:
        async def generate(self, messages):
            return ModelReply(reply="How are you?", correction="Нужно: I am happy.")

    monkeypatch.setattr(service, "get_language_model", lambda: CorrectingModel())
    headers, _ = sign_in(client)
    url = messages_url(create_dialogue(client, headers, scenario="introductions"))
    response = client.post(url, headers=headers, json={"content": "I is happy."})

    assert response.status_code == 201
    pair = response.json()
    assert pair["user_message"]["correction"] == "Нужно: I am happy."
    assert pair["assistant_message"]["correction"] is None
    assert client.get(url, headers=headers).json() == [pair["user_message"], pair["assistant_message"]]
