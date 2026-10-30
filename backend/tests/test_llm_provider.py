"""
Unit tests for modular LLM provider adapters.
"""

import pytest
from app.config import Settings
from app.llm import provider


def test_provider_adapter_selection(monkeypatch):
    """Test provider factory configuration for various models."""
    # Test Groq missing key error
    test_settings = Settings(LLM_PROVIDER="groq", GROQ_API_KEY="")
    monkeypatch.setattr(provider, "settings", test_settings)
    with pytest.raises(EnvironmentError, match="GROQ_API_KEY is required"):
        provider._build_groq()

    # Test OpenRouter missing key error
    test_settings = Settings(LLM_PROVIDER="openrouter", OPENROUTER_API_KEY="")
    monkeypatch.setattr(provider, "settings", test_settings)
    with pytest.raises(EnvironmentError, match="OPENROUTER_API_KEY is required"):
        provider._build_openrouter()

    # Test OpenAI missing key error
    test_settings = Settings(LLM_PROVIDER="openai", OPENAI_API_KEY="")
    monkeypatch.setattr(provider, "settings", test_settings)
    with pytest.raises(EnvironmentError, match="OPENAI_API_KEY is required"):
        provider._build_openai()

    # Test Unsupported provider
    test_settings = Settings(LLM_PROVIDER="invalid_provider")
    monkeypatch.setattr(provider, "settings", test_settings)
    monkeypatch.setattr(provider, "_llm_instance", None)
    with pytest.raises(ValueError, match="Unsupported LLM_PROVIDER"):
        provider.get_llm(force_new=True)


def test_ollama_provider_configuration(monkeypatch):
    """Test Ollama provider builds without external network calls."""
    test_settings = Settings(
        LLM_PROVIDER="ollama",
        LLM_MODEL="llama3.1:latest",
        OLLAMA_BASE_URL="http://localhost:11434/v1"
    )
    monkeypatch.setattr(provider, "settings", test_settings)
    chat_model = provider._build_ollama()
    assert chat_model.model_name == "llama3.1:latest"
    assert "11434" in str(chat_model.openai_api_base)

