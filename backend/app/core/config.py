"""Application Configuration Settings via Pydantic BaseSettings."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Application & Server ---
    ENVIRONMENT: str = "development"
    SERVICE_NAME: str = "qnu-ai-platform"
    API_PREFIX: str = "/platform/v1alpha1"
    PORT: int = 8001
    HOST: str = "0.0.0.0"
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8001",
    ]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [x.strip() for x in v.split(",") if x.strip()]
        if isinstance(v, list):
            return v
        return ["*"]

    # --- PostgreSQL 16 ---
    DATABASE_URL: str = "postgresql+asyncpg://qnu:qnu_password_secure_2026@localhost:5432/qnu_ai_platform"
    DB_POOL_SIZE: int = 15
    DB_MAX_OVERFLOW: int = 10
    DB_TIMEOUT_SECONDS: float = 30.0
    DEV_AUTO_MIGRATE: bool = False
    DEV_AUTO_SEED: bool = False

    # --- Qdrant Vector DB ---
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str | None = None
    QDRANT_COLLECTION: str = "qnu_knowledge_chunks"
    VECTOR_SIZE: int = 1024

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- Storage Abstraction ---
    STORAGE_DRIVER: str = "s3"  # 's3' (MinIO S3 Object Storage) hoặc 'local'
    LOCAL_STORAGE_PATH: str = "./storage"

    # S3 / MinIO Settings
    S3_ENDPOINT: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "qnu_minio_admin"
    S3_SECRET_KEY: str = "qnu_minio_secret_2026"
    S3_BUCKET: str = "qnu-ai-documents"
    S3_SECURE: bool = False
    S3_REGION: str = "us-east-1"

    # --- Gotenberg PDF Converter ---
    GOTENBERG_URL: str = "http://localhost:3005"

    # --- Embedding & Reranker ---
    EMBEDDING_PROVIDER: str = "cloudflare"  # 'cloudflare' or 'sentence_transformers'
    EMBEDDING_MODEL: str = "@cf/baai/bge-m3"
    RERANKER_PROVIDER: str = "cloudflare"  # 'cloudflare' or 'local'
    RERANKER_MODEL: str = "@cf/baai/bge-reranker-base"
    DEFAULT_TOP_K: int = 8
    DEFAULT_RERANK_TOP_K: int = 5
    MAX_CONTEXT_TOKENS: int = 6000

    # --- LLM Providers ---
    OPENAI_API_KEY: str | None = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL_NAME: str = "gpt-4o-mini"
    DEFAULT_LLM_MODEL: str = "gpt-4o-mini"

    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL_NAME: str = "gemini-2.5-flash-lite"

    # --- Mistral & Cloudflare ---
    MISTRAL_API_KEY: str | None = None
    CLOUDFLARE_API_KEY: str | None = None
    CLOUDFLARE_API_TOKEN: str | None = None
    CLOUDFLARE_ACCOUNT_ID: str | None = None

    LOCAL_LLM_ENABLED: bool = False
    LOCAL_LLM_BASE_URL: str | None = None
    LOCAL_LLM_MODEL: str = "qwen2.5:7b"

    DEFAULT_MONTHLY_TOKEN_QUOTA: int = 5_000_000
    DEFAULT_MONTHLY_COST_QUOTA_USD: float = 100.0

    # --- Security & Auth ---
    SECRET_KEY: str = "qnu-ai-platform-super-secret-key-change-in-production-2026"
    PROVIDER_ENCRYPTION_KEY: str | None = None
    OLD_PROVIDER_ENCRYPTION_KEYS: list[str] = []
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    INTERNAL_API_KEY: str = "qnu_internal_secret_key_2026"
    DEV_AUTH_ENABLED: bool = True
    DEV_ACCESS_PASSWORD: str = "QNU@2026"
    RATE_LIMIT_PER_MINUTE: int = 120

    # --- Observability ---
    LOG_LEVEL: str = "INFO"
    JSON_LOGGING: bool = True
    ENABLE_PROMETHEUS: bool = True

    @model_validator(mode="after")
    def validate_production_security(self) -> Settings:
        """Enforce strict fail-fast validation on secrets in production environment."""
        if self.ENVIRONMENT.lower() in ("production", "prod"):
            insecure_defaults = [
                ("SECRET_KEY", self.SECRET_KEY, "change-in-production"),
                ("INTERNAL_API_KEY", self.INTERNAL_API_KEY, "qnu_internal_secret_key_2026"),
                ("DEV_ACCESS_PASSWORD", self.DEV_ACCESS_PASSWORD, "QNU@2026"),
                ("DATABASE_URL", self.DATABASE_URL, "qnu_password_secure_2026"),
                ("S3_SECRET_KEY", self.S3_SECRET_KEY, "qnu_minio_secret_2026"),
            ]
            violations = [
                name for name, val, pattern in insecure_defaults
                if val and pattern in val
            ]
            if violations:
                raise ValueError(
                    f"Production security violation: Default/insecure secrets detected for {violations}. "
                    "You MUST override these variables in production environment."
                )
            if not self.PROVIDER_ENCRYPTION_KEY:
                import base64
                import hashlib

                # Deterministically derive 32-byte url-safe Fernet key from SECRET_KEY
                derived = base64.urlsafe_b64encode(hashlib.sha256(self.SECRET_KEY.encode()).digest()).decode()
                self.PROVIDER_ENCRYPTION_KEY = derived
        return self


@lru_cache
def get_settings() -> Settings:
    """Singleton getter for application settings."""
    return Settings()


settings = get_settings()
