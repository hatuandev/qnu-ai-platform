"""Cryptographic utilities for API key and secret encryption/masking."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

_FERNET_PREFIX = "enc:v1:"


def _get_fernet() -> Fernet:
    """Derive a URL-safe 32-byte Fernet key deterministically from settings.SECRET_KEY."""
    # Derive 32-byte key via SHA256
    derived = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    key_b64 = base64.urlsafe_b64encode(derived)
    return Fernet(key_b64)


def encrypt_secret(plain_text: str | None) -> str | None:
    """Encrypt a secret string using Fernet.
    
    Returns prefixed ciphertext string, e.g. 'enc:v1:gAAAAAB...'
    If plain_text is empty or None, returns plain_text as-is.
    """
    if not plain_text:
        return plain_text
    # Avoid double encryption
    if plain_text.startswith(_FERNET_PREFIX):
        return plain_text

    fernet = _get_fernet()
    encrypted_bytes = fernet.encrypt(plain_text.encode("utf-8"))
    return f"{_FERNET_PREFIX}{encrypted_bytes.decode('ascii')}"


def decrypt_secret(cipher_text: str | None) -> str | None:
    """Decrypt a secret string.
    
    If cipher_text starts with 'enc:v1:', it decrypts with Fernet.
    If it doesn't have the prefix (legacy plaintext), returns as-is for backward compatibility.
    """
    if not cipher_text:
        return cipher_text
    if not cipher_text.startswith(_FERNET_PREFIX):
        return cipher_text

    raw_token = cipher_text[len(_FERNET_PREFIX):]
    fernet = _get_fernet()
    try:
        decrypted_bytes = fernet.decrypt(raw_token.encode("ascii"))
        return decrypted_bytes.decode("utf-8")
    except (InvalidToken, ValueError):
        # In case of corruption or key rotation mismatch, return placeholder/None
        return None


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
