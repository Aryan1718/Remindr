from __future__ import annotations

import unittest

from app.core.config import Settings
from app.llm import get_llm_client
from app.llm.openai_compatible import OpenAICompatibleLLM
from app.llm.providers.gemini_openai_compatible import GeminiOpenAICompatibleLLM
from app.llm.schemas import ChatMessage, StructuredOutputSchema


class DummyResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


class DummyHttpClient:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.calls: list[dict] = []

    def post(self, url: str, *, headers: dict, json: dict):
        self.calls.append({"url": url, "headers": headers, "json": json})
        return DummyResponse(self.payload)


class LLMTests(unittest.TestCase):
    def test_openai_compatible_generate_text_parses_response(self) -> None:
        client = DummyHttpClient(
            {
                "choices": [
                    {
                        "message": {"content": "Use the resume task first."},
                        "finish_reason": "stop",
                    }
                ]
            }
        )
        llm = OpenAICompatibleLLM(
            api_key="test-key",
            model="test-model",
            base_url="https://example.com/v1",
            http_client=client,
        )

        result = llm.generate_text(messages=[ChatMessage(role="user", content="What should I do first?")])

        self.assertEqual(result.text, "Use the resume task first.")
        self.assertEqual(client.calls[0]["url"], "https://example.com/v1/chat/completions")
        self.assertEqual(client.calls[0]["json"]["messages"][0]["role"], "user")

    def test_openai_compatible_generate_structured_parses_json(self) -> None:
        client = DummyHttpClient(
            {
                "choices": [
                    {
                        "message": {"content": '{"intent":"task_capture","confidence":0.92}'},
                        "finish_reason": "stop",
                    }
                ]
            }
        )
        llm = OpenAICompatibleLLM(
            api_key="test-key",
            model="test-model",
            base_url="https://example.com/v1",
            http_client=client,
        )

        result = llm.generate_structured(
            messages=[ChatMessage(role="user", content="Task: finish resume bullets")],
            schema=StructuredOutputSchema(
                name="intent_classification",
                json_schema={
                    "type": "object",
                    "properties": {
                        "intent": {"type": "string"},
                        "confidence": {"type": "number"},
                    },
                    "required": ["intent", "confidence"],
                },
            ),
        )

        self.assertEqual(result.parsed["intent"], "task_capture")
        self.assertEqual(client.calls[0]["json"]["response_format"]["type"], "json_schema")

    def test_factory_returns_gemini_adapter_for_gemini_provider(self) -> None:
        settings = Settings.model_validate(
            {
                "llm_provider": "gemini",
                "llm_api_key": "test-key",
                "llm_model": "gemini-2.5-flash",
            }
        )

        client = get_llm_client(settings)

        self.assertIsInstance(client, GeminiOpenAICompatibleLLM)

    def test_openai_compatible_generate_embeddings_parses_vectors(self) -> None:
        client = DummyHttpClient(
            {
                "data": [
                    {"embedding": [0.1, 0.2, 0.3]},
                    {"embedding": [0.4, 0.5, 0.6]},
                ]
            }
        )
        llm = OpenAICompatibleLLM(
            api_key="test-key",
            model="text-embedding",
            base_url="https://example.com/v1",
            http_client=client,
        )

        result = llm.generate_embeddings(texts=["one", "two"])

        self.assertEqual(result, [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
        self.assertEqual(client.calls[0]["url"], "https://example.com/v1/embeddings")

    def test_settings_default_embeddings_to_openai_model(self) -> None:
        settings = Settings.model_validate(
            {
                "llm_provider": "gemini",
                "llm_api_key": "gemini-key",
                "llm_model": "gemini-2.5-flash",
                "openai_api_key": "openai-key",
            }
        )

        self.assertEqual(settings.resolved_embedding_model, "text-embedding-3-small")
        self.assertEqual(settings.resolved_openai_api_key, "openai-key")
        self.assertEqual(settings.resolved_openai_base_url, "https://api.openai.com/v1")

    def test_settings_allow_openai_llm_key_fallback_for_embeddings(self) -> None:
        settings = Settings.model_validate(
            {
                "llm_provider": "openai",
                "llm_api_key": "shared-openai-key",
                "llm_model": "gpt-4.1-mini",
            }
        )

        self.assertEqual(settings.resolved_openai_api_key, "shared-openai-key")


if __name__ == "__main__":
    unittest.main()
