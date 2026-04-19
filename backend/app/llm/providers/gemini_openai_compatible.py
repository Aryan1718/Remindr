from __future__ import annotations

from app.llm.openai_compatible import OpenAICompatibleLLM

GEMINI_OPENAI_COMPATIBLE_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"


class GeminiOpenAICompatibleLLM(OpenAICompatibleLLM):
    """Gemini implementation hidden behind the same OpenAI-compatible boundary."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str | None = None,
        timeout_seconds: float = 20.0,
        http_client=None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            model=model,
            base_url=base_url or GEMINI_OPENAI_COMPATIBLE_BASE_URL,
            timeout_seconds=timeout_seconds,
            http_client=http_client,
        )
