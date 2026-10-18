"""Интеграционные проверки теста уровня (контракт API LinguaBot)."""

import uuid

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
QUESTIONS = "/api/v1/assessment/questions"
SUBMIT = "/api/v1/assessment/submit"
RESULT = "/api/v1/assessment/result"

# Правильные ответа к фиксированному банку вопросов (идентификаторы вариантов).
CORRECT_ANSWERS = [
    {"question_id": 1, "option_id": 2},
    {"question_id": 2, "option_id": 1},
    {"question_id": 3, "option_id": 1},
    {"question_id": 4, "option_id": 3},
    {"question_id": 5, "option_id": 1},
]


def unique_email() -> str:
    return f"tester-{uuid.uuid4().hex[:10]}@example.com"


def auth_headers(client) -> dict:
    email = unique_email()
    client.post(
        REGISTER,
        json={"name": "Тест", "email": email, "password": "secret123"},
    )
    login = client.post(
        LOGIN, json={"email": email, "password": "secret123"}
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_questions_requires_auth(client):
    response = client.get(QUESTIONS)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_questions_returns_five_without_answers(client):
    response = client.get(QUESTIONS, headers=auth_headers(client))
    assert response.status_code == 200
    body = response.json()
    assert body["language"] == "en"
    assert len(body["questions"]) == 5
    for question in body["questions"]:
        assert set(question.keys()) == {"id", "text", "options"}
        assert len(question["options"]) == 4
        for option in question["options"]:
            assert set(option.keys()) == {"id", "text"}
        assert "correct" not in question
        assert "correct_option_id" not in question


def test_submit_perfect_score(client):
    response = client.post(
        SUBMIT,
        json={"answers": CORRECT_ANSWERS},
        headers=auth_headers(client),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["score"] == 100
    assert body["level"] == "advanced"
    assert body["cefr"] == "C1"
    assert body["language"] == "en"
    assert len(body["questions"]) == 5
    assert all(item["correct"] for item in body["questions"])
    assert body["taken_at"]


def test_submit_all_wrong_gives_beginner(client):
    # Зеркально неверные варианты к фиксированному банку вопросов.
    wrong = [
        {"question_id": 1, "option_id": 1},
        {"question_id": 2, "option_id": 2},
        {"question_id": 3, "option_id": 2},
        {"question_id": 4, "option_id": 1},
        {"question_id": 5, "option_id": 2},
    ]
    response = client.post(
        SUBMIT, json={"answers": wrong}, headers=auth_headers(client)
    )
    assert response.status_code == 201
    body = response.json()
    assert body["score"] == 0
    assert body["level"] == "beginner"
    assert body["cefr"] == "A1"
    assert all(not item["correct"] for item in body["questions"])


def test_result_saved_and_returned(client):
    headers = auth_headers(client)
    assert client.get(RESULT, headers=headers).status_code == 404

    client.post(SUBMIT, json={"answers": CORRECT_ANSWERS}, headers=headers)

    response = client.get(RESULT, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["score"] == 100
    assert body["level"] == "advanced"

    # Повторное прохождение перезаписывает «последний» результат.
    partial = CORRECT_ANSWERS[:3] + [
        {"question_id": 4, "option_id": 1},
        {"question_id": 5, "option_id": 2},
    ]
    client.post(SUBMIT, json={"answers": partial}, headers=headers)
    latest = client.get(RESULT, headers=headers).json()
    assert latest["score"] == 60


def test_submit_requires_auth(client):
    response = client.post(SUBMIT, json={"answers": CORRECT_ANSWERS})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_submit_rejects_missing_question(client):
    response = client.post(
        SUBMIT,
        json={"answers": CORRECT_ANSWERS[:-1]},
        headers=auth_headers(client),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_answers"


def test_submit_rejects_unknown_question(client):
    answers = CORRECT_ANSWERS[:-1] + [{"question_id": 99, "option_id": 1}]
    response = client.post(
        SUBMIT, json={"answers": answers}, headers=auth_headers(client)
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_answers"


def test_submit_rejects_wrong_option(client):
    answers = [
        {"question_id": 1, "option_id": 99},
        {"question_id": 2, "option_id": 1},
        {"question_id": 3, "option_id": 1},
        {"question_id": 4, "option_id": 3},
        {"question_id": 5, "option_id": 1},
    ]
    response = client.post(
        SUBMIT, json={"answers": answers}, headers=auth_headers(client)
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_answers"


def test_submit_rejects_duplicate_question(client):
    answers = CORRECT_ANSWERS[:-1] + [CORRECT_ANSWERS[0]]
    response = client.post(
        SUBMIT, json={"answers": answers}, headers=auth_headers(client)
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_answers"


def test_submit_requires_answers(client):
    response = client.post(
        SUBMIT, json={"answers": []}, headers=auth_headers(client)
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
