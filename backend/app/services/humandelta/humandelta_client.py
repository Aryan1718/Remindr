from __future__ import annotations

from typing import Any

import httpx


class HumanDeltaClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        timeout_seconds: float = 20.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._owns_client = client is None
        self._client = client or httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout_seconds,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
            },
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def create_index(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._client.post("/v1/indexes", json=payload)
        return self._json(response)

    def list_indexes(self, *, limit: int | None = None, offset: int | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        response = self._client.get("/v1/indexes", params=params or None)
        data = self._json(response)
        return data if isinstance(data, list) else []

    def get_index(self, index_id: str) -> dict[str, Any]:
        response = self._client.get(f"/v1/indexes/{index_id}")
        return self._json(response)

    def cancel_index(self, index_id: str) -> dict[str, Any]:
        response = self._client.post(f"/v1/indexes/{index_id}/cancel")
        return self._json(response)

    def search(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._client.post("/v1/search", json=payload)
        return self._json(response)

    def upload_document(
        self,
        *,
        file_name: str,
        content: bytes,
        content_type: str | None,
        category: str | None = None,
    ) -> dict[str, Any]:
        files = {
            "file": (
                file_name,
                content,
                content_type or "application/octet-stream",
            )
        }
        data: dict[str, Any] = {}
        if category:
            data["category"] = category
        response = self._client.post("/v1/documents", files=files, data=data or None)
        return self._json(response)

    def list_documents(self, *, category: str | None = None) -> dict[str, Any]:
        params = {"category": category} if category else None
        response = self._client.get("/v1/documents", params=params)
        return self._json(response)

    def preview_document(self, document_id: str) -> dict[str, Any]:
        response = self._client.get(f"/v1/documents/{document_id}/preview")
        return self._json(response)

    def delete_document(self, document_id: str) -> dict[str, Any]:
        response = self._client.delete(f"/v1/documents/{document_id}")
        return self._json(response)

    def run_fs(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._client.post("/v1/fs", json=payload)
        return self._json(response)

    def _json(self, response: httpx.Response) -> dict[str, Any] | list[dict[str, Any]]:
        response.raise_for_status()
        return response.json()
