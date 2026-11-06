"""Public contract for language model integrations."""

from linguabot.integrations.llm.client import (
    ChatMessage,
    LanguageModel,
    LLMError,
    LLMInvalidResponseError,
    LLMUnavailableError,
    ModelReply,
    OllamaClient,
    get_language_model,
)
from linguabot.integrations.llm.settings import LLMSettings

__all__ = [
    "ChatMessage",
    "LanguageModel",
    "LLMError",
    "LLMInvalidResponseError",
    "LLMSettings",
    "LLMUnavailableError",
    "ModelReply",
    "OllamaClient",
    "get_language_model",
]
