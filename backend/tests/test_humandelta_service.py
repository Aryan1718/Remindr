from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from fastapi import HTTPException

from app.core.config import Settings
from app.services.humandelta.humandelta_service import HumanDeltaService


class HumanDeltaServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.service = HumanDeltaService.__new__(HumanDeltaService)
        self.service.settings = Settings(
            humandelta_api_key="hd_live_test",
            humandelta_base_url="https://api.humandelta.ai",
        )
        self.service.client = self.client

    def test_create_index_builds_expected_payload(self) -> None:
        self.client.create_index.return_value = {"index_id": "idx_123", "status": "queued"}

        result = self.service.create_index(url="https://docs.example.com", name="Docs", max_pages=50)

        self.assertEqual(result["status"], "queued")
        self.client.create_index.assert_called_once_with(
            {
                "source_type": "website",
                "name": "Docs",
                "website": {"url": "https://docs.example.com", "max_pages": 50},
            }
        )

    def test_search_passes_filters_through(self) -> None:
        self.client.search.return_value = {"results": [], "query": "reset password", "total": 0}

        result = self.service.search(query="reset password", top_k=3, sources=["web"], index_id="idx_123")

        self.assertEqual(result["query"], "reset password")
        self.client.search.assert_called_once_with(
            {"query": "reset password", "top_k": 3, "sources": ["web"], "index_id": "idx_123"}
        )

    def test_upload_document_rejects_empty_content(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            self.service.upload_document(
                file_name="empty.md",
                content=b"",
                content_type="text/markdown",
            )

        self.assertEqual(ctx.exception.status_code, 422)
        self.client.upload_document.assert_not_called()


if __name__ == "__main__":
    unittest.main()
