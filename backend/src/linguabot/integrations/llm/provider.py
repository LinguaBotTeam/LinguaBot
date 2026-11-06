"""Select one provider explicitly; configuration never enables fallback."""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class ProviderSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LLM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    provider: Literal["ollama", "cloudflare"] = "ollama"
