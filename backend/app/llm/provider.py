"""
Modular LLM provider adapters.

Factory function ``get_llm()`` returns a LangChain ``BaseChatModel`` configured
from settings.

Supported providers:
- Groq (ultra-fast inference with Llama 3.3, Mixtral, etc.)
- OpenRouter (unified gateway to 200+ models from all top providers)
- OpenAI (GPT-4o, GPT-4o-mini, o1, o3-mini)
- Google Gemini (Gemini 1.5 Pro/Flash, Gemini 2.0 Flash)
- Anthropic (Claude 3.5 Sonnet, Claude 3.5 Haiku)
- DeepSeek (deepseek-chat, deepseek-coder)
- Mistral (Mistral Large, Codestral, Pixtral)
- Ollama (Local open-source models)
- Azure OpenAI (Enterprise deployed models)
- Local / Custom OpenAI-compatible endpoints (LM Studio, vLLM, LocalAI)
"""

from __future__ import annotations

from typing import Optional
from langchain_core.language_models.chat_models import BaseChatModel

from app.config import settings
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

# Cache the LLM instance (module-level singleton per process)
_llm_instance: Optional[BaseChatModel] = None


def get_llm(*, force_new: bool = False) -> BaseChatModel:
    """
    Return a configured LangChain chat model for the active provider.

    Parameters
    ----------
    force_new : bool
        If True, discard the cached instance and create a fresh one.
    """
    global _llm_instance
    if _llm_instance is not None and not force_new:
        return _llm_instance

    provider = settings.LLM_PROVIDER.lower().strip()
    logger.info("Initializing LLM provider: '%s' with model: '%s'", provider, settings.LLM_MODEL)

    if provider == "groq":
        _llm_instance = _build_groq()
    elif provider == "openrouter":
        _llm_instance = _build_openrouter()
    elif provider == "openai":
        _llm_instance = _build_openai()
    elif provider in ("gemini", "google"):
        _llm_instance = _build_gemini()
    elif provider == "anthropic":
        _llm_instance = _build_anthropic()
    elif provider == "deepseek":
        _llm_instance = _build_deepseek()
    elif provider == "mistral":
        _llm_instance = _build_mistral()
    elif provider == "ollama":
        _llm_instance = _build_ollama()
    elif provider == "azure_openai":
        _llm_instance = _build_azure_openai()
    elif provider in ("local", "custom"):
        _llm_instance = _build_local()
    else:
        raise ValueError(
            f"Unsupported LLM_PROVIDER '{provider}'. "
            "Supported options: groq, openrouter, openai, gemini, anthropic, deepseek, mistral, ollama, azure_openai, local, custom."
        )

    return _llm_instance


# ─── Provider Builder Implementations ────────────────────────────────────────

def _build_groq() -> BaseChatModel:
    """Groq Cloud adapter with ultra-fast inference."""
    if not settings.GROQ_API_KEY:
        raise EnvironmentError(
            "GROQ_API_KEY is required when LLM_PROVIDER=groq. "
            "Please provide it in your backend .env file or environment variables."
        )
    try:
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            api_key=settings.GROQ_API_KEY,
        )
    except ImportError:
        # Fallback to ChatOpenAI with Groq's OpenAI-compatible endpoint
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            api_key=settings.GROQ_API_KEY,
            base_url=settings.GROQ_BASE_URL,
        )


def _build_openrouter() -> BaseChatModel:
    """OpenRouter adapter routing to 200+ models through one API."""
    if not settings.OPENROUTER_API_KEY:
        raise EnvironmentError(
            "OPENROUTER_API_KEY is required when LLM_PROVIDER=openrouter. "
            "Please provide it in your backend .env file or environment variables."
        )
    from langchain_openai import ChatOpenAI

    headers = {"X-Title": settings.APP_NAME}
    if settings.OPENROUTER_SITE_URL:
        headers["HTTP-Referer"] = settings.OPENROUTER_SITE_URL

    return ChatOpenAI(
        model=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
        api_key=settings.OPENROUTER_API_KEY,
        base_url=settings.OPENROUTER_BASE_URL,
        default_headers=headers,
    )


def _build_openai() -> BaseChatModel:
    """Native OpenAI API adapter."""
    if not settings.OPENAI_API_KEY:
        raise EnvironmentError(
            "OPENAI_API_KEY is required when LLM_PROVIDER=openai. "
            "Please provide it in your backend .env file or environment variables."
        )
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
    )


def _build_gemini() -> BaseChatModel:
    """Google Gemini API adapter."""
    if not settings.GOOGLE_API_KEY:
        raise EnvironmentError(
            "GOOGLE_API_KEY is required when LLM_PROVIDER=gemini. "
            "Please provide it in your backend .env file or environment variables."
        )
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        max_output_tokens=settings.LLM_MAX_TOKENS,
        google_api_key=settings.GOOGLE_API_KEY,
    )


def _build_anthropic() -> BaseChatModel:
    """Anthropic Claude API adapter."""
    if not settings.ANTHROPIC_API_KEY:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic. "
            "Please provide it in your backend .env file or environment variables."
        )
    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(
        model=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
        api_key=settings.ANTHROPIC_API_KEY,
    )


def _build_deepseek() -> BaseChatModel:
    """DeepSeek API adapter."""
    if not settings.DEEPSEEK_API_KEY:
        raise EnvironmentError(
            "DEEPSEEK_API_KEY is required when LLM_PROVIDER=deepseek. "
            "Please provide it in your backend .env file or environment variables."
        )
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL,
    )


def _build_mistral() -> BaseChatModel:
    """Mistral AI API adapter."""
    if not settings.MISTRAL_API_KEY:
        raise EnvironmentError(
            "MISTRAL_API_KEY is required when LLM_PROVIDER=mistral. "
            "Please provide it in your backend .env file or environment variables."
        )
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
        api_key=settings.MISTRAL_API_KEY,
        base_url=settings.MISTRAL_BASE_URL,
    )


def _build_ollama() -> BaseChatModel:
    """Ollama local models via OpenAI compatible endpoint."""
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
        base_url=settings.OLLAMA_BASE_URL,
        api_key="ollama",  # Ollama ignores API key but requires a non-empty string in some drivers
    )


def _build_azure_openai() -> BaseChatModel:
    """Azure OpenAI API adapter."""
    if not settings.AZURE_OPENAI_API_KEY or not settings.AZURE_OPENAI_ENDPOINT:
        raise EnvironmentError(
            "AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT are required when LLM_PROVIDER=azure_openai."
        )
    from langchain_openai import AzureChatOpenAI

    return AzureChatOpenAI(
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        api_key=settings.AZURE_OPENAI_API_KEY,
        api_version=settings.AZURE_OPENAI_API_VERSION,
        azure_deployment=settings.AZURE_OPENAI_DEPLOYMENT_NAME or settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
    )


def _build_local() -> BaseChatModel:
    """Generic OpenAI-compatible local or custom server (LM Studio, vLLM, LocalAI)."""
    base_url = settings.CUSTOM_BASE_URL or settings.LOCAL_LLM_BASE_URL
    if not base_url:
        raise EnvironmentError(
            "LOCAL_LLM_BASE_URL or CUSTOM_BASE_URL is required when LLM_PROVIDER=local/custom."
        )
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
        base_url=base_url,
        api_key=settings.OPENAI_API_KEY or "not-needed",
    )
