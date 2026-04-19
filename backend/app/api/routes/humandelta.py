from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status

from app.core.security import AuthenticatedUser, get_current_user
from app.schemas.humandelta import (
    HumanDeltaEnvelope,
    HumanDeltaFsRequest,
    HumanDeltaIndexCreateRequest,
    HumanDeltaSearchRequest,
)
from app.services.humandelta import HumanDeltaService

router = APIRouter(prefix="/humandelta")


def get_humandelta_service() -> HumanDeltaService:
    return HumanDeltaService()


@router.post("/indexes", response_model=HumanDeltaEnvelope, status_code=status.HTTP_201_CREATED)
def create_index(
    payload: HumanDeltaIndexCreateRequest,
    _: AuthenticatedUser = Depends(get_current_user),
    service: HumanDeltaService = Depends(get_humandelta_service),
) -> HumanDeltaEnvelope:
    index_job = service.create_index(url=payload.url, name=payload.name, max_pages=payload.max_pages)
    return HumanDeltaEnvelope(data={"index": index_job}, message="HumanDelta index job created")


@router.get("/indexes", response_model=HumanDeltaEnvelope)
def list_indexes(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: AuthenticatedUser = Depends(get_current_user),
    service: HumanDeltaService = Depends(get_humandelta_service),
) -> HumanDeltaEnvelope:
    indexes = service.list_indexes(limit=limit, offset=offset)
    return HumanDeltaEnvelope(data={"items": indexes}, meta={"count": len(indexes), "limit": limit, "offset": offset})


@router.get("/indexes/{index_id}", response_model=HumanDeltaEnvelope)
def get_index(
    index_id: str,
    _: AuthenticatedUser = Depends(get_current_user),
    service: HumanDeltaService = Depends(get_humandelta_service),
) -> HumanDeltaEnvelope:
    index_job = service.get_index(index_id=index_id)
    return HumanDeltaEnvelope(data={"index": index_job})


@router.post("/indexes/{index_id}/cancel", response_model=HumanDeltaEnvelope)
def cancel_index(
    index_id: str,
    _: AuthenticatedUser = Depends(get_current_user),
    service: HumanDeltaService = Depends(get_humandelta_service),
) -> HumanDeltaEnvelope:
    result = service.cancel_index(index_id=index_id)
    return HumanDeltaEnvelope(data={"index": result}, message="HumanDelta index job cancelled")


@router.post("/search", response_model=HumanDeltaEnvelope)
def search(
    payload: HumanDeltaSearchRequest,
    _: AuthenticatedUser = Depends(get_current_user),
    service: HumanDeltaService = Depends(get_humandelta_service),
) -> HumanDeltaEnvelope:
    results = service.search(
        query=payload.query,
        top_k=payload.top_k,
        sources=list(payload.sources) if payload.sources else None,
        index_id=payload.index_id,
    )
    return HumanDeltaEnvelope(
        data=results,
        meta={"count": len(results.get("results", [])) if isinstance(results.get("results"), list) else 0},
    )


@router.post("/documents", response_model=HumanDeltaEnvelope, status_code=status.HTTP_201_CREATED)
def upload_document(
    file: Annotated[UploadFile, File(...)],
    category: Annotated[str | None, Form()] = None,
    _: AuthenticatedUser = Depends(get_current_user),
    service: HumanDeltaService = Depends(get_humandelta_service),
) -> HumanDeltaEnvelope:
    content = file.file.read()
    result = service.upload_document(
        file_name=file.filename or "upload.bin",
        content=content,
        content_type=file.content_type,
        category=category.strip() if category else None,
    )
    return HumanDeltaEnvelope(data=result, message="Document uploaded to HumanDelta")


@router.get("/documents", response_model=HumanDeltaEnvelope)
def list_documents(
    category: str | None = Query(default=None),
    _: AuthenticatedUser = Depends(get_current_user),
    service: HumanDeltaService = Depends(get_humandelta_service),
) -> HumanDeltaEnvelope:
    result = service.list_documents(category=category.strip() if category else None)
    documents = result.get("documents", [])
    count = len(documents) if isinstance(documents, list) else 0
    return HumanDeltaEnvelope(data=result, meta={"count": count})


@router.get("/documents/{document_id}/preview", response_model=HumanDeltaEnvelope)
def preview_document(
    document_id: str,
    _: AuthenticatedUser = Depends(get_current_user),
    service: HumanDeltaService = Depends(get_humandelta_service),
) -> HumanDeltaEnvelope:
    result = service.preview_document(document_id=document_id)
    return HumanDeltaEnvelope(data=result)


@router.delete("/documents/{document_id}", response_model=HumanDeltaEnvelope)
def delete_document(
    document_id: str,
    _: AuthenticatedUser = Depends(get_current_user),
    service: HumanDeltaService = Depends(get_humandelta_service),
) -> HumanDeltaEnvelope:
    result = service.delete_document(document_id=document_id)
    return HumanDeltaEnvelope(data=result, message="Document deleted from HumanDelta")


@router.post("/fs", response_model=HumanDeltaEnvelope)
def run_fs(
    payload: HumanDeltaFsRequest,
    _: AuthenticatedUser = Depends(get_current_user),
    service: HumanDeltaService = Depends(get_humandelta_service),
) -> HumanDeltaEnvelope:
    result = service.run_fs(payload=payload.payload_json)
    return HumanDeltaEnvelope(data=result)
