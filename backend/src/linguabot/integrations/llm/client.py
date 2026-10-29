"""Replaceable language model boundary and a local Ollama HTTP adapter."""

from typing import Literal, Protocol

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from linguabot.ai.feedback import build_correction
from linguabot.integrations.llm.response import OllamaReply
from linguabot.integrations.llm.settings import LLMSettings


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ModelReply(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", str_strip_whitespace=True)

    reply: str = Field(min_length=1, max_length=4000)
    correction: str | None = Field(max_length=3000)

    @field_validator("correction")
    @classmethod
    def normalize_blank_correction(cls, value: str | None) -> str | None:
        return value or None


class LanguageModel(Protocol):
    async def generate(self, messages: list[ChatMessage]) -> ModelReply: ...


class LLMError(Exception):
    """An error safe to translate into an application response."""


class LLMUnavailableError(LLMError):
    def __init__(self) -> None:
        super().__init__("The local language model is unavailable.")


class LLMInvalidResponseError(LLMError):
    def __init__(self) -> None:
        super().__init__("The local language model returned an invalid response.")


class OllamaClient:
    def __init__(self, settings: LLMSettings, *, transport: httpx.AsyncBaseTransport | None = None):
        self._settings = settings
        self._transport = transport

    async def generate(self, messages: list[ChatMessage]) -> ModelReply:
        if not messages or messages[-1].role != "user":
            raise LLMInvalidResponseError()
        original = messages[-1].content
        payload = {
            "model": self._settings.model,
            "messages": [message.model_dump() for message in messages],
            "stream": False,
            "think": False,
            "format": OllamaReply.model_json_schema(),
            "keep_alive": "2m",
            "options": {
                "num_ctx": self._settings.context_tokens,
                "num_predict": self._settings.max_output_tokens,
                "temperature": 0.3,
            },
        }
        try:
            async with httpx.AsyncClient(
                base_url=self._settings.base_url,
                timeout=self._settings.timeout_seconds,
                transport=self._transport,
                trust_env=False,
                follow_redirects=False,
            ) as client:
                response = await client.post("/api/chat", json=payload)
                response.raise_for_status()
        except httpx.HTTPError:
            raise LLMUnavailableError() from None

        try:
            body = response.json()
            if not isinstance(body, dict) or body.get("done") is not True or body.get("done_reason") == "length":
                raise ValueError
            message = body.get("message")
            if (
                not isinstance(message, dict)
                or message.get("role") != "assistant"
                or not isinstance(message.get("content"), str)
            ):
                raise ValueError
            generated = OllamaReply.model_validate_json(message["content"])
            return ModelReply(reply=generated.reply,
                              correction=build_correction(original, generated.corrected_text))
        except (ValueError, ValidationError):
            raise LLMInvalidResponseError() from None


def get_language_model() -> LanguageModel:
    """Construct the current provider lazily so callers can replace this boundary."""
    return OllamaClient(LLMSettings())
