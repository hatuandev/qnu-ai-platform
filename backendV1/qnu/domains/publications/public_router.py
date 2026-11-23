"""Anonymous public endpoints; no actor dependency and no internal identifiers."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.api.dependencies import get_blob_store, get_db
from qnu.domains.publications import public_service
from qnu.domains.publications.schemas import (
    PublicChatbotInfo,
    PublicChatbotListResponse,
    PublicSessionRequest,
    PublicSessionResponse,
    PublicTurnRequest,
    PublicTurnResponse,
)
from qnu.ports.blob_store import BlobStore

router = APIRouter(prefix="/public/chatbots", tags=["Public Chatbots"])
DB = Annotated[AsyncSession, Depends(get_db)]
Blob = Annotated[BlobStore, Depends(get_blob_store)]


def _requester(request: Request) -> str:
    ip = public_service.extract_client_ip(request)
    return public_service.client_key(ip)


def _apply_frame_headers(response: Response, allowed_origins: list[str] | None = None) -> None:
    """Emit server-side CSP frame-ancestors policy derived from validated embed origins."""
    origins = [o for o in (allowed_origins or []) if o]
    if origins:
        response.headers["Content-Security-Policy"] = (
            "frame-ancestors 'self' " + " ".join(origins)
        )
    else:
        response.headers["Content-Security-Policy"] = "frame-ancestors 'self'"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"


@router.get("", response_model=PublicChatbotListResponse)
async def listing(response: Response, db: DB) -> PublicChatbotListResponse:
    response.headers["Cache-Control"] = "no-store"
    _apply_frame_headers(response)
    return await public_service.listing(db)


@router.get("/{slug}", response_model=PublicChatbotInfo)
async def info(slug: str, response: Response, db: DB, blob: Blob) -> PublicChatbotInfo:
    response.headers["Cache-Control"] = "no-store"
    result = await public_service.info(db, blob, slug)
    _apply_frame_headers(response, result.allowed_embed_origins)
    return result


@router.post("/{slug}/sessions", response_model=PublicSessionResponse, status_code=201)
async def session(
    slug: str,
    request: Request,
    response: Response,
    db: DB,
    body: PublicSessionRequest | None = None,
) -> PublicSessionResponse:
    response.headers["Cache-Control"] = "no-store"
    _apply_frame_headers(response)
    return await public_service.create_session(db, slug, _requester(request), body)


@router.post("/{slug}/turns", response_model=PublicTurnResponse)
async def turn(
    slug: str,
    body: PublicTurnRequest,
    request: Request,
    response: Response,
    db: DB,
    blob: Blob,
) -> PublicTurnResponse:
    response.headers["Cache-Control"] = "no-store"
    _apply_frame_headers(response)
    container = request.app.state.container
    return await public_service.turn(
        db,
        blob,
        container.embedding_model,
        container.vector_store,
        container.chat_model,
        container.reranker,
        slug,
        body,
        _requester(request),
    )
