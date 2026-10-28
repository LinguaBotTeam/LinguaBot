"""Local model contract; all dialogue content and transports are synthetic."""

import asyncio
import json

import httpx
import pytest
from pydantic import ValidationError


def settings(**overrides):
    from linguabot.integrations.llm.settings import LLMSettings

    return LLMSettings(_env_file=None, **overrides)


def generate(handler, **overrides):
    from linguabot.integrations.llm.client import ChatMessage, OllamaClient

    client = OllamaClient(settings(**overrides), transport=httpx.MockTransport(handler))
    return asyncio.run(client.generate([ChatMessage(role="user", content="Hello!")]))


def envelope(content='{"reply":"Hello!","correction":null}', **overrides):
    return {
        "model": "qwen3:4b-instruct-2507-q4_K_M",
        "created_at": "2026-01-01T00:00:00Z",
        "message": {"role": "assistant", "content": content},
        "done": True,
        "done_reason": "stop",
        **overrides,
    }


def test_request_keeps_message_order_and_uses_local_structured_nonstreaming_options():
    from linguabot.integrations.llm.client import ChatMessage, OllamaClient

    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=envelope())

    client = OllamaClient(settings(), transport=httpx.MockTransport(handler))
    reply = asyncio.run(client.generate([
        ChatMessage(role="system", content="Synthetic tutor instructions"),
        ChatMessage(role="user", content="Hello!"),
        ChatMessage(role="assistant", content="Hello! How are you?"),
        ChatMessage(role="user", content="I am fine."),
    ]))

    assert reply.reply == "Hello!"
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "POST"
    assert str(request.url) == "http://127.0.0.1:11434/api/chat"
    body = json.loads(request.content)
    assert body["messages"] == [
        {"role": "system", "content": "Synthetic tutor instructions"},
        {"role": "user", "content": "Hello!"},
        {"role": "assistant", "content": "Hello! How are you?"},
        {"role": "user", "content": "I am fine."},
    ]
    assert set(body) == {"model", "messages", "stream", "think", "format", "keep_alive", "options"}
    assert body["model"] == "qwen3:4b-instruct-2507-q4_K_M"
    assert body["stream"] is False
    assert body["think"] is False
    assert body["keep_alive"] == "2m"
    assert body["options"] == {"num_ctx": 4096, "num_predict": 384, "temperature": 0.3}
    assert request.extensions["timeout"] == {"connect": 120, "read": 120, "write": 120, "pool": 120}
    schema = body["format"]
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"reply", "correction"}
    assert schema["properties"]["reply"]["maxLength"] == 4000
    assert schema["properties"]["correction"]["anyOf"] == [
        {"maxLength": 3000, "type": "string"}, {"type": "null"},
    ]


@pytest.mark.parametrize("correction,want", [(None, None), (" \n ", None), ("  Use 'am'.  ", "Use 'am'.")])
def test_model_reply_strips_text_and_normalizes_blank_correction(correction, want):
    result = generate(lambda request: httpx.Response(200, json=envelope(json.dumps({
        "reply": "  Hello!\n  ", "correction": correction,
    }))))
    assert result.reply == "Hello!"
    assert result.correction == want


@pytest.mark.parametrize("content", [
    "", "not JSON", "{", "[]", "null", "{}", '{"reply":"Hello!"}',
    '{"reply":"","correction":null}', '{"reply":" ","correction":null}',
    '{"reply":3,"correction":null}', '{"reply":"Hello!","correction":false}',
    '{"reply":"Hello!","correction":null,"extra":"unexpected"}',
    json.dumps({"reply": "x" * 4001, "correction": None}),
    json.dumps({"reply": "Hello!", "correction": "x" * 3001}),
])
def test_invalid_model_json_is_rejected_without_exposing_payload(content):
    from linguabot.integrations.llm.client import LLMInvalidResponseError

    with pytest.raises(LLMInvalidResponseError) as error:
        generate(lambda request: httpx.Response(200, json=envelope(content)))
    assert str(error.value) == "The local language model returned an invalid response."


@pytest.mark.parametrize("payload", [
    {}, [], None, {"error": "sensitive provider detail"},
    envelope(done=False), envelope(done="true"), envelope(done_reason="length"),
    envelope(message={}), envelope(message={"role": "assistant", "content": None}),
    envelope(message={"role": "user", "content": '{"reply":"Hi","correction":null}'}),
])
def test_invalid_or_unfinished_provider_envelope_is_rejected(payload):
    from linguabot.integrations.llm.client import LLMInvalidResponseError

    with pytest.raises(LLMInvalidResponseError):
        generate(lambda request: httpx.Response(200, json=payload))


def test_non_json_http_body_is_rejected():
    from linguabot.integrations.llm.client import LLMInvalidResponseError

    with pytest.raises(LLMInvalidResponseError):
        generate(lambda request: httpx.Response(200, content=b"invalid provider JSON"))


@pytest.mark.parametrize("status", [301, 307, 400, 404, 429, 500, 503])
def test_http_errors_are_sanitized_without_redirects_or_retries(status):
    from linguabot.integrations.llm.client import LLMUnavailableError

    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(status, text="sensitive provider detail", headers={"Location": "https://example.com"})

    with pytest.raises(LLMUnavailableError) as error:
        generate(handler)
    assert len(requests) == 1
    assert str(error.value) == "The local language model is unavailable."


@pytest.mark.parametrize("error_type", [httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout, httpx.RemoteProtocolError])
def test_transport_failures_are_sanitized_without_retries(error_type):
    from linguabot.integrations.llm.client import LLMUnavailableError

    requests = []

    def handler(request):
        requests.append(request)
        raise error_type("sensitive provider detail", request=request)

    with pytest.raises(LLMUnavailableError) as error:
        generate(handler)
    assert len(requests) == 1
    assert "sensitive" not in str(error.value)


@pytest.mark.parametrize("url", [
    "https://127.0.0.1:11434", "http://example.com", "http://192.168.1.1:11434",
    "http://0.0.0.0:11434", "http://localhost.example.com", "http://user:pass@localhost:11434",
    "http://localhost:11434?token=test", "http://localhost:11434#fragment",
    "http://localhost:11434/unexpected", "http://localhost:0", "http://localhost:99999",
    "http://127.0.0.1\\@example.com", "not a URL",
])
def test_nonlocal_or_ambiguous_model_endpoints_are_refused(url):
    with pytest.raises(ValidationError):
        settings(base_url=url)


@pytest.mark.parametrize("url", ["http://127.0.0.1:11434", "http://localhost:11434/", "http://[::1]:11434"])
def test_explicit_local_endpoints_are_accepted(url):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=envelope())

    generate(handler, base_url=url)
    assert requests[0].url.path == "/api/chat"


@pytest.mark.parametrize("model", ["gpt-oss:120b-cloud", "model:cloud", "CLOUD-model:latest", "https://ollama.com/model", "", "model with space"])
def test_cloud_or_malformed_model_tags_are_refused(model):
    with pytest.raises(ValidationError):
        settings(model=model)


@pytest.mark.parametrize("field,value", [
    ("timeout_seconds", 0), ("timeout_seconds", 301), ("timeout_seconds", float("inf")),
    ("context_tokens", 1023), ("context_tokens", 8193),
    ("max_output_tokens", 0), ("max_output_tokens", 1025),
])
def test_resource_limits_are_bounded(field, value):
    with pytest.raises(ValidationError):
        settings(**{field: value})


def test_custom_limits_are_passed_to_provider():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=envelope())

    generate(handler, timeout_seconds=30, context_tokens=2048, max_output_tokens=200)
    assert json.loads(requests[0].content)["options"] == {"num_ctx": 2048, "num_predict": 200, "temperature": 0.3}
    assert requests[0].extensions["timeout"]["read"] == 30


def test_prefixed_settings_read_safe_dotenv_without_other_app_settings(tmp_path, monkeypatch):
    from linguabot.integrations.llm.settings import LLMSettings

    for key in ("LLM_BASE_URL", "LLM_MODEL", "LLM_TIMEOUT_SECONDS", "LLM_CONTEXT_TOKENS", "LLM_MAX_OUTPUT_TOKENS"):
        monkeypatch.delenv(key, raising=False)
    dotenv = tmp_path / ".env"
    dotenv.write_text("LLM_TIMEOUT_SECONDS=45\nLLM_CONTEXT_TOKENS=2048\nAPP_NAME=Synthetic\n", encoding="utf-8")
    result = LLMSettings(_env_file=dotenv)
    assert result.timeout_seconds == 45
    assert result.context_tokens == 2048


def test_factory_reads_current_settings_and_returns_replaceable_client(monkeypatch):
    from linguabot.integrations.llm import get_language_model
    from linguabot.integrations.llm.client import OllamaClient

    monkeypatch.setenv("LLM_BASE_URL", "https://example.com")
    with pytest.raises(ValidationError):
        get_language_model()
    monkeypatch.setenv("LLM_BASE_URL", "http://127.0.0.1:11434")
    assert isinstance(get_language_model(), OllamaClient)


def test_chat_messages_reject_unrecognized_roles():
    from linguabot.integrations.llm.client import ChatMessage

    with pytest.raises(ValidationError):
        ChatMessage(role="tool", content="Synthetic")
