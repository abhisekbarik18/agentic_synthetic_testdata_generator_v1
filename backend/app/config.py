"""
Application configuration loaded exclusively from environment variables / .env file.
"""

from __future__ import annotations

from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central settings — loaded from environment variables and .env file."""

    # ── Application ──────────────────────────────────────────────────────
    APP_NAME: str = "Agentic Test Data Simulator"
    DEBUG: bool = False

    # ── Database ─────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./tdm.db"

    # ── LLM Provider ────────────────────────────────────────────────────
    # Options: openai, gemini, anthropic, groq, openrouter, deepseek, mistral, ollama, azure_openai, local
    LLM_PROVIDER: str = "groq"
    LLM_MODEL: str = "llama-3.3-70b-versatile"
    LLM_TEMPERATURE: float = 0.7

    # ── API Keys & Base URLs ─────────────────────────────────────────────
    # Groq
    GROQ_API_KEY: Optional[str] = None
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"

    # OpenRouter
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_SITE_URL: Optional[str] = None

    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"

    # Google Gemini
    GOOGLE_API_KEY: Optional[str] = None

    # Anthropic
    ANTHROPIC_API_KEY: Optional[str] = None

    # DeepSeek
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"

    # Mistral
    MISTRAL_API_KEY: Optional[str] = None
    MISTRAL_BASE_URL: str = "https://api.mistral.ai/v1"

    # Ollama / Local / Generic OpenAI-Compatible
    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
    LOCAL_LLM_BASE_URL: str = "http://localhost:1234/v1"
    CUSTOM_BASE_URL: Optional[str] = None

    # Azure OpenAI
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_ENDPOINT: Optional[str] = None
    AZURE_OPENAI_API_VERSION: str = "2024-02-15-preview"
    AZURE_OPENAI_DEPLOYMENT_NAME: Optional[str] = None

    # ── Generation Limits ────────────────────────────────────────────────
    MAX_RECORDS_PER_REQUEST: int = 10_000
    MAX_RETRIES: int = 3
    BATCH_SIZE: int = 50
    LLM_MAX_TOKENS: int = 8192

    # ── Export ───────────────────────────────────────────────────────────
    EXPORT_DIR: str = "exports"
    MAX_EXPORT_FILE_SIZE_MB: int = 100

    # ── CORS ─────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = []

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
