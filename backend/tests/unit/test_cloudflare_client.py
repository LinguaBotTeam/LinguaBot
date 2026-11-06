"""Cloudflare boundary tests use only synthetic credentials and HTTP data."""

import asyncio
import json

import httpx
import pytest
from pydantic import ValidationError

from linguabot.integrations.llm.client import (
    ChatMessage,
    LLMInvalidResponseError,
    LLMUnavailableError,
)


def settings(**overrides):
    from linguabot.integrations.llm.cloudflare_settings import (
        CloudflareSettings,
    )

    values = {
        "account_id": "a" * 32,
        "api_token": "synthetic-test-token",
        **overrides,
    }
    return CloudflareSettings(_env_file=None, **values)


def envelope(response=None, **result_fields):
    if response is None:
        response = {"reply": "Hello! How are you?", "corrected_text": None}
    return {
        "success": True,
        "errors": [],
        "result": {"response": response, **result_fields},
    }


def generate(handler, messages=None):
    from linguabot.integrations.llm.cloudflare import CloudflareClient

    model = CloudflareClient(
        settings(), transport=httpx.MockTransport(handler)
    )
    if messages is None:
        messages = [ChatMessage(role="user", content="Hello!")]
    return asyncio.run(model.generate(messages))


@pytest.mark.parametrize("as_string", [False, True])
def test_cloudflare_sends_context_and_validates_structured_reply(as_string):
    requests = []
    answer = {
        "reply": "Of course. What size do you need?",
        "corrected_text": "These shoes are small.",
    }

    def handler(request):
        requests.append(request)
        value = json.dumps(answer) if as_string else answer
        return httpx.Response(200, json=envelope(value))

    messages = [
        ChatMessage(role="system", content="Synthetic tutor instructions"),
        ChatMessage(role="user", content="I need shoes."),
        ChatMessage(role="assistant", content="Which shoes?"),
        ChatMessage(role="user", content="These shoes is small."),
    ]
    result = generate(handler, messages)
    assert result.reply == "Of course. What size do you need?"
    assert 'Заменено "is" на "are".' in result.correction
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "POST"
    assert str(request.url) == (
        "https://api.cloudflare.com/client/v4/accounts/"
        + "a" * 32
        + "/ai/run/@cf/meta/llama-3.3-70b-instruct-fp8-fast"
    )
    assert request.headers["Authorization"] == "Bearer synthetic-test-token"
    body = json.loads(request.content)
    assert body["messages"] == [m.model_dump() for m in messages]
    assert body["stream"] is False
    assert 1 <= body["max_tokens"] <= 1024
    assert set(body) == {
        "messages", "stream", "max_tokens", "temperature", "response_format",
    }
    schema = body["response_format"]["json_schema"]
    assert body["response_format"]["type"] == "json_schema"
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"reply", "corrected_text"}
    assert "synthetic-test-token" not in request.content.decode()
    assert request.extensions["timeout"]["read"] <= 120


@pytest.mark.parametrize("corrected", [None, "Hello!"])
def test_no_correction_stays_null(corrected):
    result = generate(lambda r: httpx.Response(200, json=envelope({
        "reply": "Hello! How are you?", "corrected_text": corrected,
    })))
    assert result.correction is None


@pytest.mark.parametrize("status", [301, 307, 400, 401, 403, 429, 500, 503])
def test_http_failure_never_retries_redirects_or_changes_model(status):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(
            status, text="synthetic private provider detail",
            headers={"Location": "https://example.invalid"},
        )

    with pytest.raises(LLMUnavailableError) as error:
        generate(handler)
    assert len(requests) == 1
    assert "private" not in str(error.value)
    assert "synthetic-test-token" not in str(error.value)


@pytest.mark.parametrize("error_type", [
    httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError,
])
def test_transport_failure_is_sanitized_without_retry(error_type):
    requests = []

    def handler(request):
        requests.append(request)
        raise error_type("synthetic-test-token", request=request)

    with pytest.raises(LLMUnavailableError) as error:
        generate(handler)
    assert len(requests) == 1
    assert "synthetic-test-token" not in str(error.value)


@pytest.mark.parametrize("payload", [
    None, [], {}, {"success": "true", "result": {}},
    {"success": True, "result": []},
    {"success": True, "result": {"response": None}},
    envelope("not JSON"), envelope("[]"), envelope("{}"),
    envelope({"reply": "Hi"}),
    envelope({"reply": "", "corrected_text": None}),
    envelope({"reply": "Hi", "corrected_text": False}),
    envelope({"reply": "Hi", "corrected_text": None, "extra": "bad"}),
    envelope({"reply": "x" * 4001, "corrected_text": None}),
    envelope({"reply": "Hi", "corrected_text": "x" * 4001}),
    envelope({"reply": "\ud800", "corrected_text": None}),
    envelope({"reply": "Hi", "corrected_text": "\ud800"}),
    envelope(finish_reason="length"),
])
def test_invalid_response_is_rejected_without_leaking_content(payload):
    with pytest.raises(LLMInvalidResponseError):
        generate(lambda r: httpx.Response(
            200, content=json.dumps(payload).encode("ascii")
        ))


def test_non_json_http_body_is_rejected():
    with pytest.raises(LLMInvalidResponseError):
        generate(lambda r: httpx.Response(200, content=b"invalid JSON"))


def test_provider_failure_with_http_200_is_unavailable():
    with pytest.raises(LLMUnavailableError):
        generate(lambda r: httpx.Response(200, json={
            "success": False, "errors": [{"code": 3036}], "result": None,
        }))


def test_complete_feedback_limit_is_not_silently_clipped():
    with pytest.raises(LLMInvalidResponseError):
        generate(lambda r: httpx.Response(200, json=envelope({
            "reply": "Hello!", "corrected_text": "b" * 3000,
        })))


@pytest.mark.parametrize("messages", [
    [], [ChatMessage(role="assistant", content="Hello!")],
])
def test_missing_current_user_message_never_calls_http(messages):
    def forbidden(request):
        pytest.fail("Invalid input must not reach the provider")

    with pytest.raises(LLMInvalidResponseError):
        generate(forbidden, messages)


@pytest.mark.parametrize("account_id", [
    "", "a" * 31, "a" * 33, "g" * 32, "../other-account", "a" * 32 + "\n",
])
def test_unsafe_account_identifier_is_rejected(account_id):
    with pytest.raises(ValidationError):
        settings(account_id=account_id)


@pytest.mark.parametrize("token", ["", " ", "a\nb", "a\rb", "Bearer token"])
def test_token_cannot_inject_headers_or_be_empty(token):
    with pytest.raises(ValidationError):
        settings(api_token=token)


def test_secret_is_hidden_and_unapproved_model_is_rejected():
    configured = settings()
    assert "synthetic-test-token" not in repr(configured)
    with pytest.raises(ValidationError):
        settings(model="@cf/unknown/paid-model")


@pytest.mark.parametrize("overrides", [
    {"timeout_seconds": 0}, {"timeout_seconds": float("inf")},
    {"timeout_seconds": 121}, {"max_output_tokens": 0},
    {"max_output_tokens": 1025},
])
def test_resource_limits_are_bounded(overrides):
    with pytest.raises(ValidationError):
        settings(**overrides)
