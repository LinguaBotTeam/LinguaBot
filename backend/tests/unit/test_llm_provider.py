"""Provider selection stays explicit and never contacts a model at setup."""

import httpx
import pytest
from pydantic import ValidationError

from linguabot.integrations.llm import get_language_model
from linguabot.integrations.llm.client import OllamaClient
from linguabot.integrations.llm.cloudflare import CloudflareClient


@pytest.fixture(autouse=True)
def isolated_config(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    for name in (
        "LLM_PROVIDER", "CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_API_TOKEN",
        "CLOUDFLARE_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LLM_BASE_URL", "http://127.0.0.1:11434")


def test_default_ollama_does_not_require_cloud_settings(monkeypatch):
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "invalid-unused-setting")
    assert isinstance(get_language_model(), OllamaClient)


def test_cloudflare_selection_does_not_validate_local_settings(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "cloudflare")
    monkeypatch.setenv("LLM_BASE_URL", "https://invalid-local-origin")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "a" * 32)
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "synthetic-test-token")
    assert isinstance(get_language_model(), CloudflareClient)


@pytest.mark.parametrize("provider", ["", "unknown", "Cloudflare"])
def test_unrecognized_provider_never_silently_falls_back(
    monkeypatch, provider,
):
    monkeypatch.setenv("LLM_PROVIDER", provider)
    with pytest.raises(ValidationError):
        get_language_model()


def test_missing_cloud_credentials_never_falls_back(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "cloudflare")
    with pytest.raises(ValidationError):
        get_language_model()


def test_factory_creates_client_without_sending_http(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Construction must not send HTTP")

    monkeypatch.setenv("LLM_PROVIDER", "cloudflare")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "a" * 32)
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "synthetic-test-token")
    monkeypatch.setattr(httpx.AsyncClient, "post", forbidden)
    assert isinstance(get_language_model(), CloudflareClient)
