from __future__ import annotations

from app.core.config import Settings, get_settings
from app.llm.base import BaseLLMClient
from app.llm.openai_compatible import OpenAICompatibleLLM
from app.llm.providers.gemini_openai_compatible import GeminiOpenAICompatibleLLM


def get_llm_client(settings: Settings | None = None) -> BaseLLMClient | None:
    active_settings = settings or get_settings()
    if not active_settings.llm_api_key or not active_settings.llm_model or not active_settings.resolved_llm_base_url:
        return None

    provider = active_settings.llm_provider.lower()
    if provider == "gemini":
        return GeminiOpenAICompatibleLLM(
            api_key=active_settings.llm_api_key,
            model=active_settings.llm_model,
            base_url=active_settings.resolved_llm_base_url,
            timeout_seconds=active_settings.llm_timeout_seconds,
        )

    return OpenAICompatibleLLM(
        api_key=active_settings.llm_api_key,
        model=active_settings.llm_model,
        base_url=active_settings.resolved_llm_base_url,
        timeout_seconds=active_settings.llm_timeout_seconds,
    )
