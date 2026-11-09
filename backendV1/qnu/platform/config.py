"""Single source of configuration for backendV1.

Retired output-cap and vector-collection env names (COMPILER_MAX_OUTPUT_TOKENS,
RAG_MAX_OUTPUT_TOKENS, CONVERSATION_REWRITE_MAX_OUTPUT_TOKENS, QDRANT_COLLECTION,
VECTOR_SIZE) are intentionally absent: budgets and vector dimensions come from
ModelOps/the embedding runtime, and collections are named per index run.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven settings with safe local defaults."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENVIRONMENT: str = "development"
    SERVICE_NAME: str = "qnu-backend-v1"
    API_PREFIX: str = "/platform/v1alpha1"
    HOST: str = "0.0.0.0"
    PORT: int = 8002
    # Browser-visible URL, never inferred from request headers or frontend origin.
    PUBLIC_BASE_URL: AnyHttpUrl | None = None
    LOG_LEVEL: str = "INFO"
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    DATABASE_URL: str = "postgresql+asyncpg://localhost/qnu_backend_v1"
    REDIS_URL: str = "redis://localhost:6379/3"
    QUEUE_NAME: str = "qnu:v1:jobs"
    CACHE_NAMESPACE: str = "qnu:v1:cache:"

    STORAGE_DRIVER: Literal["local", "s3"] = "local"
    LOCAL_STORAGE_PATH: str = "./storage"
    S3_ENDPOINT: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET: str = "qnu-ai-documents"
    S3_SECURE: bool = False

    QDRANT_URL: str = "http://localhost:6333"

    SECRET_KEY: str = ""
    INTERNAL_API_KEY: str = ""
    PROVIDER_ENCRYPTION_KEY: str = ""

    DEV_AUTH_ENABLED: bool = True
    DEV_ACCESS_PASSWORD: str = ""
    SSO_ENABLED: bool = False
    SSO_AUTHORITY: str = ""
    SSO_AUDIENCE: str = "ai.api"
    SSO_JWKS_URL: str = ""
    SSO_JWKS_CACHE_SECONDS: int = Field(300, ge=1, le=3600)

    HTTP_TIMEOUT_SECONDS: float = Field(default=30.0, gt=0)
    MAX_UPLOAD_BYTES: int = Field(default=60 * 1024 * 1024, gt=0)
    GOTENBERG_URL: str = Field(default="http://127.0.0.1:3005")
    DOCX_CONVERTER: Literal["gotenberg-libreoffice", "docx-story"] = "gotenberg-libreoffice"
    # Change when deploying a different converter image/fonts/options to invalidate reuse.
    DOCX_RENDERER_REVISION: str = Field(default="qnu-docx/v2", min_length=1, max_length=200)

    # OCR processing (Context640). Values are pinned into every run fingerprint.
    OCR_RENDER_DPI: int = Field(default=144, ge=72, le=300)
    OCR_MAX_PAGES: int = Field(default=300, ge=1, le=2000)
    OCR_MAX_PAGE_BYTES: int = Field(default=8 * 1024 * 1024, ge=65536)
    # Optional operator override for legacy image OCR; MinerU does not use LLM tokens.
    OCR_MAX_OUTPUT_TOKENS: int | None = Field(default=None, ge=1)
    OCR_PAGE_TOKEN_BUDGET: int = Field(default=8192, ge=1, le=10**9)
    OCR_RUN_MAX_ATTEMPTS: int = Field(default=2, ge=1, le=5)
    OCR_LEASE_SECONDS: int = Field(default=900, ge=60)
    OCR_DISPATCH_ENABLED: bool = True
    COMPILER_LEASE_SECONDS: int = Field(default=900, ge=60)
    # Independent parts may overlap, but the provider is shared with every other
    # caller: keep this small and below the server's own concurrency.
    COMPILER_SEGMENT_CONCURRENCY: int = Field(default=2, ge=1, le=4)
    # Shared Redis admission for all managed chat calls to the same endpoint/model.
    # Operational policy, not a claim about discovered server max_num_seqs.
    MODEL_CHAT_CONCURRENCY: int = Field(default=4, ge=1, le=64)
    MODEL_CHAT_QUEUE_TIMEOUT_SECONDS: int = Field(default=300, ge=1, le=3600)
    PUBLICATION_PREVIEW_TTL_SECONDS: int = Field(default=300, ge=1, le=3600)
    # Optional operator override; otherwise chunk sizing follows the embedding runtime.
    INDEX_CHUNK_MAX_BYTES: int | None = Field(default=None, ge=256)
    INDEX_EMBED_BATCH_SIZE: int = Field(default=16, ge=1, le=128)
    INDEX_MAX_DOCUMENTS: int = Field(default=100, ge=1, le=1000)
    INDEX_MAX_CHUNKS: int = Field(default=20000, ge=1)
    INDEX_LEASE_SECONDS: int = Field(default=900, ge=60)
    INDEX_MAX_ATTEMPTS: int = Field(default=3, ge=1, le=10)
    INDEX_RETAIN_INACTIVE: int = Field(default=1, ge=0)
    INDEX_RETIRE_AFTER_SECONDS: int = Field(default=86400, ge=0)
    CONVERSATION_TURN_LEASE_SECONDS: int = Field(default=900, ge=60)
    CONVERSATION_HISTORY_MAX_BYTES: int = Field(default=16000, ge=1024)
    # Ownership rule (docs/runtime-ownership.md): only one backend reconciles its own queue.
    OWN_RECONCILE: bool = True
    # Model jobs may span many independent pages/parts. This is an operational
    # safety ceiling, distinct from provider read timeouts and renewable leases.
    WORKER_MODEL_JOB_TIMEOUT_SECONDS: int = Field(default=86400, ge=60)

    @property
    def allowed_origins(self) -> list[str]:
        return [item.strip() for item in self.ALLOWED_ORIGINS.split(",") if item.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in ("production", "prod")


@lru_cache
def get_settings() -> Settings:
    return Settings()
