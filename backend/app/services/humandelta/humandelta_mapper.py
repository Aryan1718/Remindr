from __future__ import annotations

from typing import Any


def build_index_create_payload(
    *,
    url: str,
    name: str | None = None,
    max_pages: int | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "source_type": "website",
        "website": {"url": url},
    }
    if name:
        payload["name"] = name
    if max_pages is not None:
        payload["website"]["max_pages"] = max_pages
    return payload


def build_search_payload(
    *,
    query: str,
    top_k: int | None = None,
    sources: list[str] | None = None,
    index_id: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"query": query}
    if top_k is not None:
        payload["top_k"] = top_k
    if sources:
        payload["sources"] = sources
    if index_id:
        payload["index_id"] = index_id
    return payload

