"""Composition root for adapters; domains receive ports, never SDK clients."""

from __future__ import annotations

from dataclasses import dataclass

from qnu.adapters.providers.embedding import ModelOpsEmbeddingModel
from qnu.adapters.providers.nemotron import NemotronOcrEngine
from qnu.adapters.providers.openai_compatible import OpenAICompatibleChatModel
from qnu.adapters.providers.reranker import ModelOpsReranker
from qnu.adapters.queue.arq_queue import ArqJobQueue
from qnu.adapters.storage.local import LocalBlobStore
from qnu.adapters.storage.s3 import S3BlobStore
from qnu.adapters.vector.qdrant import QdrantVectorStore
from qnu.domains.modelops.resilience.execution import (
    ManagedChatModel,
    ManagedEmbeddingModel,
    ManagedOcrEngine,
    ManagedReranker,
)
from qnu.platform.config import Settings
from qnu.ports.blob_store import BlobStore
from qnu.ports.chat_model import ChatModel
from qnu.ports.embedding_model import EmbeddingModel
from qnu.ports.job_queue import JobQueue
from qnu.ports.ocr_engine import OcrEngine
from qnu.ports.reranker import Reranker
from qnu.ports.vector_store import VectorStore


@dataclass(slots=True)
class Container:
    """Resolved adapters for one process."""

    settings: Settings
    blob_store: BlobStore
    job_queue: JobQueue | None = None
    ocr_engine: OcrEngine | None = None
    chat_model: ChatModel | None = None
    embedding_model: EmbeddingModel | None = None
    vector_store: VectorStore | None = None
    reranker: Reranker | None = None


def build_container(settings: Settings) -> Container:
    if settings.STORAGE_DRIVER == "s3":
        blob_store: BlobStore = S3BlobStore(settings)
    else:
        blob_store = LocalBlobStore(settings.LOCAL_STORAGE_PATH)
    queue: JobQueue = ArqJobQueue(settings.REDIS_URL, settings.QUEUE_NAME)
    return Container(
        settings=settings,
        blob_store=blob_store,
        job_queue=queue,
        ocr_engine=ManagedOcrEngine(NemotronOcrEngine()),
        chat_model=ManagedChatModel(OpenAICompatibleChatModel()),
        embedding_model=ManagedEmbeddingModel(ModelOpsEmbeddingModel()),
        vector_store=QdrantVectorStore(settings.QDRANT_URL),
        reranker=ManagedReranker(ModelOpsReranker()),
    )


async def close_container(container: Container) -> None:
    close = getattr(container.blob_store, "close", None)
    if close is not None:
        await close()
    if container.job_queue is not None:
        queue_close = getattr(container.job_queue, "close", None)
        if queue_close is not None:
            await queue_close()
