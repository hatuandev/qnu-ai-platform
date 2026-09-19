"""Cryptographic utilities for API key and secret encryption/masking.

Supports versioned Fernet tokens (prefix 'enc:v1:') and Key Rotation.
"""

from __future__ import annotations

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

logger = logging.getLogger(__name__)

_FERNET_PREFIX = "enc:v1:"


def _derive_fernet(raw_key: str) -> Fernet:
    """Derive a URL-safe 32-byte Fernet key deterministically from a raw key string."""
    derived = hashlib.sha256(raw_key.encode("utf-8")).digest()
    key_b64 = base64.urlsafe_b64encode(derived)
    return Fernet(key_b64)


def _get_active_fernet() -> Fernet:
    """Derive the primary active Fernet instance."""
    enc_key = settings.PROVIDER_ENCRYPTION_KEY or settings.SECRET_KEY
    return _derive_fernet(enc_key)


def _get_fallback_fernets() -> list[Fernet]:
    """Get list of Fernet instances for older rotated keys."""
    old_keys = settings.OLD_PROVIDER_ENCRYPTION_KEYS or []
    if isinstance(old_keys, str):
        old_keys = [k.strip() for k in old_keys.split(",") if k.strip()]
    return [_derive_fernet(k) for k in old_keys]


def is_encrypted(val: str | None) -> bool:
    """Check if value is already encrypted with Fernet prefix."""
    if not val:
        return False
    return val.startswith(_FERNET_PREFIX)


def encrypt_secret(plain_text: str | None) -> str | None:
    """Encrypt a secret string using the active Fernet key.

    Returns prefixed ciphertext string, e.g. 'enc:v1:gAAAAAB...'
    If plain_text is empty or None, returns plain_text as-is.
    """
    if not plain_text:
        return plain_text
    # Avoid double encryption
    if plain_text.startswith(_FERNET_PREFIX):
        return plain_text

    fernet = _get_active_fernet()
    encrypted_bytes = fernet.encrypt(plain_text.encode("utf-8"))
    return f"{_FERNET_PREFIX}{encrypted_bytes.decode('ascii')}"


def decrypt_secret(cipher_text: str | None) -> str | None:
    """Decrypt a secret string with key rotation support.

    If cipher_text starts with 'enc:v1:', attempts decryption with the active key.
    If decryption fails and older keys are configured, tries each older key.
    If it doesn't have the prefix (legacy plaintext), returns as-is for backward compatibility.
    """
    if not cipher_text:
        return cipher_text
    if not cipher_text.startswith(_FERNET_PREFIX):
        return cipher_text

    raw_token = cipher_text[len(_FERNET_PREFIX):].encode("ascii")

    # 1. Try active key
    active_fernet = _get_active_fernet()
    try:
        decrypted_bytes = active_fernet.decrypt(raw_token)
        return decrypted_bytes.decode("utf-8")
    except (InvalidToken, ValueError):
        pass

    # 2. Try older keys in rotation window
    fallback_fernets = _get_fallback_fernets()
    for fallback in fallback_fernets:
        try:
            decrypted_bytes = fallback.decrypt(raw_token)
            return decrypted_bytes.decode("utf-8")
        except (InvalidToken, ValueError):
            continue

    # In case of corruption or key rotation mismatch, log error and return None
    logger.error("Failed to decrypt secret token: invalid token or missing rotation key.")
    return None


def reencrypt_secret(cipher_text: str | None) -> str | None:
    """Decrypt a secret (using active or older key) and re-encrypt with the active key.

    Useful for key rotation migration runs.
    """
    if not cipher_text:
        return cipher_text
    plain = decrypt_secret(cipher_text)
    if plain is None:
        logger.warning("Cannot re-encrypt: secret could not be decrypted.")
        return cipher_text
    return encrypt_secret(plain)


def mask_secret(secret: str | None) -> str | None:
    """Mask a secret string for safe display in API responses and logs.

    Examples:
      'sk-proj-1234567890abcdef' -> '••••••••cdef'
      'short' -> '••••'
      None / '' -> None
    """
    if not secret:
        return None

    # If secret is an encrypted token, decrypt first to get the last 4 characters of the real key
    real_secret = decrypt_secret(secret) if secret.startswith(_FERNET_PREFIX) else secret
    if not real_secret:
        return "••••••••"

    length = len(real_secret)
    if length <= 8:
        return "••••"

    last_four = real_secret[-4:]
    return f"••••••••{last_four}"
