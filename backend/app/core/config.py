"""Application settings loaded from environment / .env file."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration for the PromptGrade backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./promptgrade.db",
        description="SQLAlchemy async database URL.",
    )

    # Logging
    log_level: str = Field(default="INFO")

    # LLM provider keys (all optional — BYOK)
    anthropic_api_key: str | None = Field(default=None)
    openai_api_key: str | None = Field(default=None)
    google_api_key: str | None = Field(default=None)
    groq_api_key: str | None = Field(default=None)

    # Ollama
    ollama_base_url: str = Field(default="http://localhost:11434")

    # Judge selection (auto-detected when not set)
    judge_provider: str | None = Field(default=None)
    judge_model: str | None = Field(default=None)

    # Hybrid grader weights
    rules_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    llm_weight: float = Field(default=0.7, ge=0.0, le=1.0)


settings = Settings()
