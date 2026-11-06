"""Resource limits and local-only configuration for the language model."""

import ipaddress
import re
from urllib.parse import urlsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LLM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    base_url: str = "http://127.0.0.1:11434"
    model: str = "qwen3:4b-instruct-2507-q4_K_M"
    timeout_seconds: float = Field(default=120, gt=0, le=300, allow_inf_nan=False)
    context_tokens: int = Field(default=4096, ge=1024, le=8192)
    max_output_tokens: int = Field(default=384, ge=1, le=1024)

    @field_validator("base_url")
    @classmethod
    def require_loopback_http(cls, value: str) -> str:
        error = "LLM base URL must be an HTTP loopback origin without credentials or extra URL components"
        if any(char.isspace() for char in value) or any(char in value for char in "\\?#"):
            raise ValueError(error)
        try:
            url = urlsplit(value)
            host = url.hostname
            port = url.port
            if (
                url.scheme != "http"
                or not host
                or url.username is not None
                or url.password is not None
                or url.path not in ("", "/")
                or (port is not None and not 1 <= port <= 65535)
                or url.netloc.endswith(":")
            ):
                raise ValueError(error)
            if host != "localhost" and not ipaddress.ip_address(host).is_loopback:
                raise ValueError(error)
        except ValueError:
            raise ValueError(error) from None
        return value.rstrip("/")

    @field_validator("model")
    @classmethod
    def require_local_model_tag(cls, value: str) -> str:
        if "cloud" in value.lower() or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*(?::[A-Za-z0-9._-]+)?", value):
            raise ValueError("LLM model must be a local model tag without cloud routing")
        return value
