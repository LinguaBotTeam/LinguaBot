"""Scenario API routing with real auth/storage and a recording model.

All learner details and credentials in this file are synthetic test data.
"""

import uuid

import pytest

from linguabot.integrations.llm import ChatMessage, ModelReply
from linguabot.modules.dialogues import service
from linguabot.modules.dialogues.scenarios import scenario_instructions


class RecordingModel:
    def __init__(self) -> None:
        self.calls: list[list[ChatMessage]] = []

    async def generate(self, messages: list[ChatMessage]) -> ModelReply:
        self.calls.append(messages)
        return ModelReply(
            reply="Could you tell me more?", correction="Тестовая правка.",
        )


@pytest.fixture()
def model(monkeypatch):
    recording = RecordingModel()
    monkeypatch.setattr(service, "get_language_model", lambda: recording)
    return recording


@pytest.fixture()
def headers(client):
    email = f"synthetic-scenario-{uuid.uuid4().hex}@example.com"
    credentials = {"email": email, "password": "synthetic-test-password"}
    registered = client.post(
        "/api/v1/auth/register",
        json={"name": "Synthetic learner", **credentials},
    )
    assert registered.status_code == 201
    login = client.post("/api/v1/auth/login", json=credentials)
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.mark.parametrize("key,role", [
    ("introductions", "language club"),
    ("cafe", "barista"),
    ("shop", "shop assistant"),
    ("travel", "check-in"),
    ("business_meeting", "business partner"),
    ("doctor_visit", "general practitioner"),
    ("renting_a_flat", "landlord"),
    ("customer_support", "support agent"),
    ("job_interview", "HR interviewer"),
    ("weekend_small_talk", "acquaintance"),
])
def test_every_scenario_creates_chat_and_reaches_model(
    client, headers, model, key, role,
):
    title = "Title is not a scenario instruction"
    created = client.post(
        "/api/v1/dialogues", headers=headers,
        json={"title": title, "scenario": key},
    )
    assert created.status_code == 201
    dialogue = created.json()
    assert dialogue["scenario"] == key
    assert dialogue["title"] == title
    assert dialogue["project_id"] is None
    url = f"/api/v1/dialogues/{dialogue['id']}/messages"
    sent = client.post(url, headers=headers, json={"content": "Hello!"})
    assert sent.status_code == 201

    assert len(model.calls) == 1
    system, current = model.calls[0]
    assert system.role == "system"
    assert role in system.content
    assert scenario_instructions(key) in system.content
    assert title not in system.content
    assert "Trusted learner CEFR: A1." in system.content
    assert (current.role, current.content) == ("user", "Hello!")
    pair = sent.json()
    assert pair["user_message"]["correction"] == "Тестовая правка."
    assert pair["assistant_message"]["correction"] is None
    history = client.get(url, headers=headers)
    assert history.status_code == 200
    assert history.json() == [
        pair["user_message"], pair["assistant_message"],
    ]


def test_new_scenario_continues_only_its_own_history(client, headers, model):
    def new_chat(key):
        created = client.post(
            "/api/v1/dialogues", headers=headers, json={"scenario": key},
        )
        assert created.status_code == 201
        return f"/api/v1/dialogues/{created.json()['id']}/messages"

    travel = new_chat("travel")
    interview = new_chat("job_interview")
    first = client.post(
        travel, headers=headers, json={"content": "I have one suitcase."},
    )
    assert first.status_code == 201
    assert client.post(
        interview, headers=headers,
        json={"content": "I have three years of experience."},
    ).status_code == 201
    assert client.post(
        travel, headers=headers, json={"content": "An aisle seat, please."},
    ).status_code == 201

    messages = model.calls[-1]
    assert [message.role for message in messages] == [
        "system", "user", "assistant", "user",
    ]
    assert messages[0].content == model.calls[0][0].content
    assert [message.content for message in messages[1:]] == [
        "I have one suitcase.", "Could you tell me more?",
        "An aisle seat, please.",
    ]
    assert "experience" not in " ".join(
        message.content for message in messages[1:]
    )
    assert len(client.get(travel, headers=headers).json()) == 4
