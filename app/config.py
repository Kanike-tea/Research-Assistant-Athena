"""Application configuration loaded from environment variables."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment variables."""
    # LLM Settings
    LLM_MODEL: str = Field(
        default="llama3.2",
        description="The Ollama model to use for generation."
    )
    LLM_TEMPERATURE: float = Field(
        default=0.1,
        description="Temperature for sampling."
    )
    
    # Optional: Ollama host if not running locally
    OLLAMA_BASE_URL: str = Field(
        default="http://localhost:11434",
        description="Base URL for the Ollama server."
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
