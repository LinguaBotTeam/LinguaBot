"""Интеграционные проверки грамматических упражнений."""

import uuid

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
ASSESSMENT_SUBMIT = "/api/v1/assessment/submit"
NEXT = "/api/v1/exercises/next"

CORRECT_ANSWERS = [
    {"question_id": 1, "option_id": 2},
    {"question_id": 2, "option_id": 1},
    {"question_id": 3, "option_id": 1},
    {"question_id": 4, "option_id": 3},
    {"question_id": 5, "option_id": 1},
]

WRONG_ANSWERS = [
    {"question_id": 1, "option_id": 1},
    {"question_id": 2, "option_id": 2},
    {"question_id": 3, "option_id": 2},
    {"question_id": 4, "option_id": 1},
    {"question_id": 5, "option_id": 2},
]

# Известные верные варианты первых заданий каждого уровня.
FIRST_EXERCISE = {
    "beginner": (101, 2),
    "intermediate": (201, 3),
    "advanced": (301, 3),
}


def unique_email() -> str:
    return f"exercise-{uuid.uuid4().hex[:10]}@example.com"


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


def user_with_level(client, answers: list[dict]) -> dict:
    headers = auth_headers(client)
    response = client.post(
        ASSESSMENT_SUBMIT, json={"answers": answers}, headers=headers
    )
    assert response.status_code == 201
    return headers


def answer(client, headers: dict, exercise_id: int, option_id: int):
    return client.post(
        f"/api/v1/exercises/{exercise_id}/answer",
        json={"option_id": option_id},
        headers=headers,
    )


def test_next_requires_auth(client):
    response = client.get(NEXT)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_answer_requires_auth(client):
    response = client.post(
        "/api/v1/exercises/101/answer", json={"option_id": 2}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_without_test_result_defaults_to_beginner(client):
    response = client.get(NEXT, headers=auth_headers(client))
    assert response.status_code == 200
    body = response.json()
    assert body["difficulty"] == "beginner"
    assert body["level_source"] == "default"
    assert body["id"] == FIRST_EXERCISE["beginner"][0]
    assert body["topic"]
    assert len(body["options"]) == 4
    for option in body["options"]:
        assert set(option.keys()) == {"id", "text"}
    assert "correct_option_id" not in body
    assert "explanation" not in body


def test_difficulty_comes_from_advanced_result(client):
    headers = user_with_level(client, CORRECT_ANSWERS)
    body = client.get(NEXT, headers=headers).json()
    assert body["difficulty"] == "advanced"
    assert body["level_source"] == "test"
    assert body["id"] == FIRST_EXERCISE["advanced"][0]


def test_difficulty_comes_from_intermediate_result(client):
    answers = CORRECT_ANSWERS[:3] + WRONG_ANSWERS[3:]
    headers = user_with_level(client, answers)
    body = client.get(NEXT, headers=headers).json()
    assert body["difficulty"] == "intermediate"
    assert body["level_source"] == "test"
    assert body["id"] == FIRST_EXERCISE["intermediate"][0]


def test_difficulty_comes_from_beginner_result(client):
    headers = user_with_level(client, WRONG_ANSWERS)
    body = client.get(NEXT, headers=headers).json()
    assert body["difficulty"] == "beginner"
    assert body["level_source"] == "test"
    assert body["id"] == FIRST_EXERCISE["beginner"][0]


def test_exclude_returns_another_exercise(client):
    headers = auth_headers(client)
    body = client.get(NEXT + "?exclude=101", headers=headers).json()
    assert body["id"] == 102


def test_correct_and_wrong_answers_on_each_level(client):
    scenarios = [
        ("beginner", WRONG_ANSWERS),
        ("intermediate", CORRECT_ANSWERS[:3] + WRONG_ANSWERS[3:]),
        ("advanced", CORRECT_ANSWERS),
    ]
    for difficulty, assessment_answers in scenarios:
        headers = user_with_level(client, assessment_answers)
        exercise_id, correct_option_id = FIRST_EXERCISE[difficulty]

        right = answer(client, headers, exercise_id, correct_option_id)
        assert right.status_code == 200
        right_body = right.json()
        assert right_body["difficulty"] == difficulty
        assert right_body["correct"] is True
        assert right_body["correct_option_id"] == correct_option_id
        assert right_body["correct_text"]
        assert right_body["explanation"]
        assert right_body["selected_option_id"] == correct_option_id

        wrong_option_id = next(
            option_id
            for option_id in (1, 2, 3, 4)
            if option_id != correct_option_id
        )
        wrong = answer(client, headers, exercise_id, wrong_option_id)
        assert wrong.status_code == 200
        wrong_body = wrong.json()
        assert wrong_body["difficulty"] == difficulty
        assert wrong_body["correct"] is False
        assert wrong_body["correct_option_id"] == correct_option_id
        assert wrong_body["correct_text"]
        assert wrong_body["explanation"]
        assert wrong_body["selected_option_id"] == wrong_option_id


def test_unknown_exercise_returns_not_found(client):
    response = answer(client, auth_headers(client), 999, 1)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "exercise_not_found"


def test_unknown_option_is_rejected(client):
    response = answer(client, auth_headers(client), 101, 99)
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "invalid_option"
    assert error["field"] == "option_id"


def test_answer_requires_option(client):
    response = client.post(
        "/api/v1/exercises/101/answer",
        json={},
        headers=auth_headers(client),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
