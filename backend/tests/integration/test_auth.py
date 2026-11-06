"""Интеграционные проверки регистрации и входа (контракт API LinguaBot)."""

import uuid

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"


def unique_email() -> str:
    return f"user-{uuid.uuid4().hex[:10]}@example.com"


def register_payload(email: str) -> dict:
    return {"name": "Тест", "email": email, "password": "secret123"}


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_register_returns_user_without_token(client):
    email = unique_email()
    response = client.post(REGISTER, json=register_payload(email))
    assert response.status_code == 201
    body = response.json()
    assert set(body.keys()) == {"id", "name", "email"}
    assert body["email"] == email
    assert body["name"] == "Тест"
    assert "access_token" not in body
    assert "password" not in body
    assert "password_hash" not in body


def test_duplicate_email_is_rejected(client):
    email = unique_email()
    assert client.post(REGISTER, json=register_payload(email)).status_code == 201
    response = client.post(REGISTER, json=register_payload(email))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_taken"


def test_login_returns_token_and_user(client):
    email = unique_email()
    client.post(REGISTER, json=register_payload(email))

    response = client.post(LOGIN, json={"email": email, "password": "secret123"})
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["token_type"] == "Bearer"
    assert isinstance(body["expires_in"], int) and body["expires_in"] > 0
    assert body["user"]["email"] == email

    me = client.get(ME, headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert set(me.json().keys()) == {"id", "name", "email"}


def test_login_with_wrong_password(client):
    email = unique_email()
    client.post(REGISTER, json=register_payload(email))
    response = client.post(LOGIN, json={"email": email, "password": "wrong-password"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


def test_me_requires_token(client):
    response = client.get(ME)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_register_validates_short_password(client):
    response = client.post(
        REGISTER, json={"name": "Тест", "email": unique_email(), "password": "short"}
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["field"] == "password"


def test_register_requires_email(client):
    response = client.post(REGISTER, json={"name": "Тест", "password": "secret123"})
    assert response.status_code == 422
    assert response.json()["error"]["field"] == "email"
