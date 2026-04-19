from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException, status

from app.core.config import Settings, get_settings
from app.services.humandelta.humandelta_client import HumanDeltaClient
from app.services.humandelta.humandelta_mapper import build_index_create_payload, build_search_payload


class HumanDeltaService:
    def __init__(
        self,
        settings: Settings | None = None,
        client: HumanDeltaClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.client = client or self._build_client()

    def create_index(
        self,
        *,
        url: str,
        name: str | None = None,
        max_pages: int | None = None,
    ) -> dict[str, Any]:
        return self._call(
            lambda: self.client.create_index(
                build_index_create_payload(url=url, name=name, max_pages=max_pages)
            )
        )

    def list_indexes(self, *, limit: int | None = None, offset: int | None = None) -> list[dict[str, Any]]:
        return self._call(lambda: self.client.list_indexes(limit=limit, offset=offset))

    def get_index(self, *, index_id: str) -> dict[str, Any]:
        return self._call(lambda: self.client.get_index(index_id))

    def cancel_index(self, *, index_id: str) -> dict[str, Any]:
        return self._call(lambda: self.client.cancel_index(index_id))

    def search(
        self,
        *,
        query: str,
        top_k: int | None = None,
        sources: list[str] | None = None,
        index_id: str | None = None,
    ) -> dict[str, Any]:
        return self._call(
            lambda: self.client.search(
                build_search_payload(query=query, top_k=top_k, sources=sources, index_id=index_id)
            )
        )

    def upload_document(
        self,
        *,
        file_name: str,
        content: bytes,
        content_type: str | None,
        category: str | None = None,
    ) -> dict[str, Any]:
        if not content:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Document upload content is empty",
            )
        return self._call(
            lambda: self.client.upload_document(
                file_name=file_name,
                content=content,
                content_type=content_type,
                category=category,
            )
        )

    def list_documents(self, *, category: str | None = None) -> dict[str, Any]:
        return self._call(lambda: self.client.list_documents(category=category))

    def preview_document(self, *, document_id: str) -> dict[str, Any]:
        return self._call(lambda: self.client.preview_document(document_id))

    def delete_document(self, *, document_id: str) -> dict[str, Any]:
        return self._call(lambda: self.client.delete_document(document_id))

    def run_fs(self, *, payload: dict[str, Any]) -> dict[str, Any]:
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="HumanDelta fs payload cannot be empty",
            )
        return self._call(lambda: self.client.run_fs(payload))

    def _build_client(self) -> HumanDeltaClient:
        if not self.settings.humandelta_api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="HumanDelta API key is not configured",
            )
        if not self.settings.humandelta_base_url:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="HumanDelta base URL is not configured",
            )
        return HumanDeltaClient(
            api_key=self.settings.humandelta_api_key,
            base_url=self.settings.humandelta_base_url,
            timeout_seconds=self.settings.humandelta_timeout_seconds,
        )

    def _call(self, operation: Any) -> Any:
        try:
            return operation()
        except HTTPException:
            raise
        except httpx.TimeoutException as exc:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="HumanDelta request timed out",
            ) from exc
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text.strip() or exc.response.reason_phrase
            raise HTTPException(
                status_code=exc.response.status_code,
                detail=f"HumanDelta API error: {detail}",
            ) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="HumanDelta API is unavailable",
            ) from exc
