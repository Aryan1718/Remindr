from __future__ import annotations

from abc import ABC, abstractmethod

from app.llm.schemas import ChatMessage, LLMStructuredResult, LLMTextResult, StructuredOutputSchema


class BaseLLMClient(ABC):
    """Provider-neutral LLM interface exposed to application services."""

    @abstractmethod
    def generate_text(
        self,
        *,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> LLMTextResult:
        raise NotImplementedError

    @abstractmethod
    def generate_structured(
        self,
        *,
        messages: list[ChatMessage],
        schema: StructuredOutputSchema,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> LLMStructuredResult:
        raise NotImplementedError

    @abstractmethod
    def generate_embeddings(
        self,
        *,
        texts: list[str],
        model: str | None = None,
    ) -> list[list[float]]:
        raise NotImplementedError
