"""Конфигурация приложения, читается из окружения и файла .env."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Корень репозитория: backend/src/linguabot/core/config.py -> parents[4]
_REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "LinguaBot API"
    api_v1_prefix: str = "/api/v1"

    # Каталог со статическим frontend, который раздаёт backend.
    frontend_dir: str = str(_REPO_ROOT / "frontend")

    # SQLite по умолчанию, чтобы проект запускался без внешних сервисов.
    # Для PostgreSQL замените значение, например на:
    # postgresql+asyncpg://linguabot:linguabot@localhost:5432/linguabot
    database_url: str = "sqlite+aiosqlite:///./linguabot.db"

    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7

    # "*" удобно для локальной разработки. В продакшене укажите конкретные источники.
    cors_origins: list[str] = ["*"]


settings = Settings()
