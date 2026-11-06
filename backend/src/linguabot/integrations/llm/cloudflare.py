"""One-shot Workers AI adapter; never upgrades or changes providers."""

import httpx

from linguabot.ai.feedback import build_correction
from linguabot.integrations.llm.client import (
    ChatMessage,
    LLMInvalidResponseError,
    LLMUnavailableError,
    ModelReply,
)
from linguabot.integrations.llm.cloudflare_settings import CloudflareSettings
from linguabot.integrations.llm.response import OllamaReply as GeneratedReply


class CloudflareClient:
    def __init__(
        self,
        settings: CloudflareSettings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._settings = settings
        self._transport = transport

    async def generate(self, messages: list[ChatMessage]) -> ModelReply:
        if not messages or messages[-1].role != "user":
            raise LLMInvalidResponseError()
        settings = self._settings
        url = (
            "https://api.cloudflare.com/client/v4/accounts/"
            f"{settings.account_id}/ai/run/{settings.model}"
        )
        payload = {
            "messages": [message.model_dump() for message in messages],
            "stream": False,
            "max_tokens": settings.max_output_tokens,
            "temperature": 0.3,
            "response_format": {
                "type": "json_schema",
                "json_schema": GeneratedReply.model_json_schema(),
            },
        }
        try:
            async with httpx.AsyncClient(
                timeout=settings.timeout_seconds,
                transport=self._transport,
                trust_env=False,
                follow_redirects=False,
            ) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={
                        "Authorization": (
                            f"Bearer {settings.api_token.get_secret_value()}"
                        ),
                    },
                )
                response.raise_for_status()
        except httpx.HTTPError:
            raise LLMUnavailableError() from None

        try:
            body = response.json()
            if not isinstance(body, dict):
                raise ValueError
            if body.get("success") is False:
                raise LLMUnavailableError()
            if body.get("success") is not True:
                raise ValueError
            result = body.get("result")
            if not isinstance(result, dict):
                raise ValueError
            if result.get("finish_reason") in ("length", "content_filter"):
                raise ValueError
            content = result.get("response")
            if isinstance(content, str):
                generated = GeneratedReply.model_validate_json(content)
            else:
                generated = GeneratedReply.model_validate(content)
            generated.reply.encode("utf-8")
            if generated.corrected_text is not None:
                generated.corrected_text.encode("utf-8")
            return ModelReply(
                reply=generated.reply,
                correction=build_correction(
                    messages[-1].content, generated.corrected_text
                ),
            )
        except ValueError:
            raise LLMInvalidResponseError() from None
