"""Application Configuration Settings via Pydantic BaseSettings."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from pydantic import AliasChoices, Field, field_validator, model_validator
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

    @field_validator(
        "QDRANT_API_KEY",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "MISTRAL_API_KEY",
        "CLOUDFLARE_API_KEY",
        "CLOUDFLARE_API_TOKEN",
        "NVIDIA_API_KEY",
        "GOTENBERG_USERNAME",
        "GOTENBERG_PASSWORD",
        mode="before",
    )
    @classmethod
    def empty_str_to_none(cls, v: Any) -> Any:
        if isinstance(v, str) and not v.strip():
            return None
        return v

    # --- PostgreSQL 16 ---
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://qnu:qnu_password_secure_2026@localhost:5432/qnu_ai_platform",
        validation_alias=AliasChoices("DATABASE_URL", "CONNECTION_STRING", "POSTGRES_URL"),
    )
    DB_POOL_SIZE: int = 15
    DB_MAX_OVERFLOW: int = 10
    DB_TIMEOUT_SECONDS: float = 30.0
    DEV_AUTO_MIGRATE: bool = False
    DEV_AUTO_SEED: bool = False

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def parse_database_url(cls, v: Any) -> Any:
        if not isinstance(v, str):
            return v
        v = v.strip()
        if not v:
            return v

        # Tự động chuyển đổi nếu là chuỗi kết nối dạng ADO.NET / Npgsql (Host=...;Port=...;Database=...;Username=...;Password=...)
        if "=" in v and (";" in v or "host=" in v.lower() or "server=" in v.lower()):
            import urllib.parse

            parts: dict[str, str] = {}
            for token in v.split(";"):
                token = token.strip()
                if not token or "=" not in token:
                    continue
                k, val = token.split("=", 1)
                parts[k.strip().lower()] = val.strip()

            host = parts.get("host") or parts.get("server") or "localhost"
            port = parts.get("port") or "5432"
            database = parts.get("database") or parts.get("initial catalog") or "qnu_ai_platform"
            username = parts.get("username") or parts.get("user id") or parts.get("user") or "admin"
            password = parts.get("password") or parts.get("pwd") or ""

            enc_user = urllib.parse.quote_plus(username)
            enc_pass = urllib.parse.quote_plus(password)

            ssl_mode = parts.get("ssl mode", "").lower()
            ssl_query = ""
            if ssl_mode in ("require", "verify-ca", "verify-full"):
                ssl_query = f"?ssl={ssl_mode}"

            return f"postgresql+asyncpg://{enc_user}:{enc_pass}@{host}:{port}/{database}{ssl_query}"

        # Đảm bảo dùng asyncpg driver cho SQLAlchemy async
        if v.startswith("postgres://"):
            return "postgresql+asyncpg://" + v[len("postgres://"):]
        if v.startswith("postgresql://") and not v.startswith("postgresql+"):
            return "postgresql+asyncpg://" + v[len("postgresql://"):]

        return v

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

    # S3 / MinIO Settings (Hỗ trợ cả chuẩn S3_* và chuẩn Dokploy MINIO_* / FILE_STORAGE_*)
    S3_ENDPOINT: str = Field(
        default="http://localhost:9000",
        validation_alias=AliasChoices("S3_ENDPOINT", "FILE_STORAGE_ENDPOINT", "MINIO_ENDPOINT"),
    )
    S3_ACCESS_KEY: str = Field(
        default="qnu_minio_admin",
        validation_alias=AliasChoices(
            "S3_ACCESS_KEY", "MINIO_ROOT_USER", "FILE_STORAGE_ACCESS_KEY", "MINIO_ACCESS_KEY"
        ),
    )
    S3_SECRET_KEY: str = Field(
        default="qnu_minio_secret_2026",
        validation_alias=AliasChoices(
            "S3_SECRET_KEY", "MINIO_ROOT_PASSWORD", "FILE_STORAGE_SECRET_KEY", "MINIO_SECRET_KEY"
        ),
    )
    S3_BUCKET: str = Field(
        default="qnu-ai-documents",
        validation_alias=AliasChoices("S3_BUCKET", "FILE_STORAGE_BUCKET", "MINIO_BUCKET"),
    )
    S3_SECURE: bool = Field(
        default=False,
        validation_alias=AliasChoices("S3_SECURE", "FILE_STORAGE_USE_SSL", "MINIO_USE_SSL"),
    )
    S3_REGION: str = "us-east-1"

    # --- Gotenberg PDF Converter ---
    GOTENBERG_URL: str = Field(
        default="http://localhost:3005",
        validation_alias=AliasChoices("GOTENBERG_URL", "GOTENBERG_BASE_URL", "GOTENBERG_BASEURL"),
    )
    GOTENBERG_USERNAME: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GOTENBERG_USERNAME", "GOTENBERG_USER"),
    )
    GOTENBERG_PASSWORD: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GOTENBERG_PASSWORD", "GOTENBERG_PASS"),
    )

    @property
    def gotenberg_auth(self) -> tuple[str, str] | None:
        """Returns Basic Auth tuple for Gotenberg if credentials are provided."""
        if self.GOTENBERG_USERNAME and self.GOTENBERG_PASSWORD:
            return (self.GOTENBERG_USERNAME, self.GOTENBERG_PASSWORD)
        if "@" in self.GOTENBERG_URL:
            import urllib.parse
            parsed = urllib.parse.urlsplit(self.GOTENBERG_URL)
            if parsed.username and parsed.password:
                return (parsed.username, parsed.password)
        return None

    @property
    def clean_gotenberg_url(self) -> str:
        """Returns clean Gotenberg base URL stripped of any embedded auth or trailing slash."""
        url = self.GOTENBERG_URL.rstrip("/")
        if "@" in url:
            import urllib.parse
            parsed = urllib.parse.urlsplit(url)
            port_part = f":{parsed.port}" if parsed.port else ""
            return f"{parsed.scheme}://{parsed.hostname}{port_part}"
        return url

    # --- Embedding & Reranker ---
    EMBEDDING_PROVIDER: str = "custom"
    EMBEDDING_MODEL: str = "bge-m3:latest"
    RERANKER_PROVIDER: str = "cloudflare"
    RERANKER_MODEL: str = "@cf/baai/bge-reranker-base"
    DEFAULT_TOP_K: int = 8
    DEFAULT_RERANK_TOP_K: int = 5
    MAX_CONTEXT_TOKENS: int = 6000

    # --- LLM Providers ---
    OPENAI_API_KEY: str | None = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL_NAME: str = "gpt-4o-mini"
    DEFAULT_LLM_MODEL: str = "gpt-4o-mini"

    # --- vLLM Local Server (Tailscale / On-Premise) ---
    VLLM_BASE_URL: str = Field(
        default="http://tormemrtxproto.tail0924dd.ts.net:8000/v1",
        validation_alias=AliasChoices("VLLM_BASE_URL", "VLLM_URL"),
    )

    # --- Ollama / Local AI Server (Tailscale / On-Premise) ---
    OLLAMA_BASE_URL: str = Field(
        default="http://tormemrtxproto.tail0924dd.ts.net:11434",
        validation_alias=AliasChoices("OLLAMA_BASE_URL", "OLLAMA_HOST"),
    )

    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL_NAME: str = "gemini-2.5-flash-lite"

    # --- Mistral & Cloudflare ---
    MISTRAL_API_KEY: str | None = None
    CLOUDFLARE_API_KEY: str | None = None
    CLOUDFLARE_API_TOKEN: str | None = None
    CLOUDFLARE_ACCOUNT_ID: str | None = None

    # --- NVIDIA NIM ---
    NVIDIA_API_KEY: str | None = None
    NVIDIA_BASE_URL: str = Field(
        default="https://integrate.api.nvidia.com/v1",
        validation_alias=AliasChoices("NVIDIA_BASE_URL", "NVIDIA_API_BASE", "NVIDIA_NIM_URL"),
    )

    # --- OpenRouter ---
    OPENROUTER_API_KEY: str | None = None
    OPENROUTER_BASE_URL: str = Field(
        default="https://openrouter.ai/api/v1",
        validation_alias=AliasChoices("OPENROUTER_BASE_URL", "OPENROUTER_API_BASE", "OPENROUTER_URL"),
    )

    DEFAULT_MONTHLY_TOKEN_QUOTA: int = 5_000_000
    DEFAULT_MONTHLY_COST_QUOTA_USD: float = 100.0

    # --- ADR-011 Knowledge Publishing V2 & Cutover ---
    RAG_REVISION_READ_MODE: str = "revisioned"  # "legacy" | "shadow" | "revisioned"
    KNOWLEDGE_REVISION_WRITES_ENABLED: bool = True
    KNOWLEDGE_GC_RETENTION_REVISIONS: int = 2
    KNOWLEDGE_ALLOW_DIRECT_UPLOAD: bool = False  # Decommissioning guard: khi False, cấm upload trực tiếp vào collection, buộc nạp qua Kho Tài Liệu V2

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

    # --- QNU Single Sign-On (OIDC / OpenIddict) ---
    SSO_ENABLED: bool = True
    SSO_AUTHORITY: str = Field(
        default="http://localhost:5000",
        validation_alias=AliasChoices("SSO_AUTHORITY", "AUTH_AUTHORITY"),
    )
    SSO_CLIENT_ID: str = Field(
        default="qnu-ai-platform",
        validation_alias=AliasChoices("SSO_CLIENT_ID", "AUTH_CLIENT_ID"),
    )
    SSO_AUDIENCE: str = "ai.api"
    SSO_JWKS_URL: str | None = None
    SSO_USERINFO_URL: str | None = None

    @property
    def clean_sso_authority(self) -> str:
        """Returns clean SSO Authority base URL without trailing slash."""
        return self.SSO_AUTHORITY.rstrip("/")

    @property
    def sso_jwks_url(self) -> str:
        """Endpoint to fetch public JSON Web Key Sets (JWKS) from QNU SSO."""
        if self.SSO_JWKS_URL:
            return self.SSO_JWKS_URL
        return f"{self.clean_sso_authority}/.well-known/jwks"

    @property
    def sso_userinfo_url(self) -> str:
        """OIDC UserInfo endpoint on QNU SSO."""
        if self.SSO_USERINFO_URL:
            return self.SSO_USERINFO_URL
        return f"{self.clean_sso_authority}/connect/userinfo"

    # --- Observability ---
    LOG_LEVEL: str = "INFO"
    JSON_LOGGING: bool = True
    ENABLE_PROMETHEUS: bool = True

    @model_validator(mode="after")
    def validate_production_security(self) -> Settings:
        """Enforce strict fail-fast validation on secrets in production environment."""
        # Tự động kích hoạt SSL nếu endpoint là HTTPS
        if self.S3_ENDPOINT and self.S3_ENDPOINT.lower().startswith("https://"):
            self.S3_SECURE = True

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
                raise ValueError(
                    "Production security violation: PROVIDER_ENCRYPTION_KEY must be configured."
                )
        return self


@lru_cache
def get_settings() -> Settings:
    """Singleton getter for application settings."""
    return Settings()


settings = get_settings()


def resolve_ollama_network_url(url: str | None = None) -> str:
    """Resolve Ollama endpoint URL with resilience for Tailscale MagicDNS fallback."""
    import socket
    from urllib.parse import urlparse, urlunparse

    target_url = (url or getattr(settings, "OLLAMA_BASE_URL", "") or "http://tormemrtxproto.tail0924dd.ts.net:11434").strip()
    if not target_url:
        return ""

    parsed = urlparse(target_url)
    hostname = parsed.hostname or ""
    if not hostname:
        return target_url

    try:
        socket.gethostbyname(hostname)
        return target_url
    except socket.gaierror:
        # Fallback mapping if Tailscale MagicDNS is not yet enabled on the local client
        tailscale_map = {
            "tormemrtxproto.tail0924dd.ts.net": "100.105.13.53",
            "tormemrtxproto": "100.105.13.53",
        }
        if hostname in tailscale_map:
            ip = tailscale_map[hostname]
            netloc = f"{ip}:{parsed.port}" if parsed.port else ip
            return urlunparse(parsed._replace(netloc=netloc))
        return target_url
