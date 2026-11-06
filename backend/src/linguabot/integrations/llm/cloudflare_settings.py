"""Explicit Workers AI credentials and bounded generation settings."""

from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class CloudflareSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CLOUDFLARE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
        hide_input_in_errors=True,
    )

    account_id: str = Field(
        min_length=32, max_length=32, pattern=r"^[a-fA-F0-9]{32}$"
    )
    api_token: SecretStr
    model: Literal["@cf/meta/llama-3.3-70b-instruct-fp8-fast"] = (
        "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
    )
    timeout_seconds: float = Field(
        default=60, gt=0, le=120, allow_inf_nan=False
    )
    max_output_tokens: int = Field(default=512, ge=1, le=1024)

    @field_validator("api_token")
    @classmethod
    def require_header_safe_token(cls, value: SecretStr) -> SecretStr:
        token = value.get_secret_value()
        if not 1 <= len(token) <= 4096 or any(
            not 33 <= ord(char) <= 126 for char in token
        ):
            raise ValueError("A nonempty header-safe API token is required.")
        return value
