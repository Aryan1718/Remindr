from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.routes.humandelta import get_humandelta_service
from app.core.security import AuthenticatedUser, get_current_user
from app.main import create_app


class _FakeHumanDeltaService:
    def create_index(self, *, url: str, name: str | None = None, max_pages: int | None = None) -> dict:
        return {
            "index_id": "idx_123",
            "status": "queued",
            "seed_url": url,
            "name": name,
            "max_pages": max_pages,
        }

    def list_indexes(self, *, limit: int | None = None, offset: int | None = None) -> list[dict]:
        return [{"index_id": "idx_123", "status": "completed"}]

    def get_index(self, *, index_id: str) -> dict:
        return {"index_id": index_id, "status": "completed"}

    def cancel_index(self, *, index_id: str) -> dict:
        return {"index_id": index_id, "status": "cancelled"}

    def search(
        self,
        *,
        query: str,
        top_k: int | None = None,
        sources: list[str] | None = None,
        index_id: str | None = None,
    ) -> dict:
        return {
            "results": [{"chunk_id": "chunk:1", "score": 0.81, "text": f"match for {query}"}],
            "query": query,
            "total": 1,
            "top_k": top_k,
            "sources": sources,
            "index_id": index_id,
        }

    def upload_document(
        self,
        *,
        file_name: str,
        content: bytes,
        content_type: str | None,
        category: str | None = None,
    ) -> dict:
        return {
            "success": True,
            "document": {
                "id": "doc_123",
                "doc_name": file_name,
                "category": category,
                "file_size": len(content),
                "file_type": content_type,
            },
        }

    def list_documents(self, *, category: str | None = None) -> dict:
        return {"documents": [{"id": "doc_123", "category": category}], "total": 1}

    def preview_document(self, *, document_id: str) -> dict:
        return {"id": document_id, "content_text": "Preview text"}

    def delete_document(self, *, document_id: str) -> dict:
        return {"success": True, "document_id": document_id}

    def run_fs(self, *, payload: dict) -> dict:
        return {"output": "tree /docs", "request": payload}


def _build_client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(user_id="user-1", auth_user_id="auth-1")
    app.dependency_overrides[get_humandelta_service] = _FakeHumanDeltaService
    return TestClient(app)


def test_create_index_route() -> None:
    client = _build_client()

    response = client.post(
        "/api/v1/humandelta/indexes",
        json={"url": "https://docs.example.com", "name": "Help Center", "max_pages": 50},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["data"]["index"]["index_id"] == "idx_123"
    assert body["data"]["index"]["seed_url"] == "https://docs.example.com"


def test_search_route() -> None:
    client = _build_client()

    response = client.post(
        "/api/v1/humandelta/search",
        json={"query": "reset password", "top_k": 3, "sources": ["web"], "index_id": "idx_123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["query"] == "reset password"
    assert body["meta"]["count"] == 1


def test_upload_document_route() -> None:
    client = _build_client()

    response = client.post(
        "/api/v1/humandelta/documents",
        data={"category": "gmail"},
        files={"file": ("digest.md", b"# Inbox digest", "text/markdown")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["data"]["document"]["id"] == "doc_123"
    assert body["data"]["document"]["category"] == "gmail"


def test_fs_route() -> None:
    client = _build_client()

    response = client.post(
        "/api/v1/humandelta/fs",
        json={"payload_json": {"command": "tree", "path": "/"}},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["request"]["command"] == "tree"
