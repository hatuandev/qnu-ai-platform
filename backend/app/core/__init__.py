"""Core Package Initialization — Central Export for Foundational Services."""

from app.core.config import Settings, get_settings
from app.core.database import AsyncSessionFactory, Base, check_db_health, engine, get_db
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    DomainException,
    EntityAlreadyExistsError,
    EntityNotFoundError,
    RateLimitExceededError,
    register_exception_handlers,
)
from app.core.guardrails import input_guardrail, output_guardrail
from app.core.logging import configure_logging, get_logger
from app.core.middleware import setup_middlewares
from app.core.redis import check_redis_health, get_redis_client, semantic_cache
from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    hash_api_key,
    mask_pii,
    verify_password,
)
from app.core.storage import storage_service

__all__ = [
    "AsyncSessionFactory",
    "AuthenticationError",
    "AuthorizationError",
    "Base",
    "DomainException",
    "EntityAlreadyExistsError",
    "EntityNotFoundError",
    "RateLimitExceededError",
    "Settings",
    "check_db_health",
    "check_redis_health",
    "configure_logging",
    "create_access_token",
    "decode_access_token",
    "engine",
    "get_db",
    "get_logger",
    "get_password_hash",
    "get_redis_client",
    "get_settings",
    "hash_api_key",
    "input_guardrail",
    "mask_pii",
    "output_guardrail",
    "register_exception_handlers",
    "semantic_cache",
    "setup_middlewares",
    "storage_service",
    "verify_password",
]
