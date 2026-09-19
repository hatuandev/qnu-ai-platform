"""Provider Secrets Migration Tool — QNU AI Platform.

Encrypts plaintext API keys in PostgreSQL `model_provider_configs` table
and validates that 100% of stored secrets use versioned ciphertext ('enc:v1:').

Modes:
    --dry-run : Inspect current database secrets, count plaintext vs encrypted (no changes).
    --apply   : Encrypt all plaintext keys and re-encrypt rotated keys within a transaction.
    --verify  : Validate that zero plaintext secrets remain and all ciphertexts decrypt properly.

Usage:
    uv run python scripts/migrate_provider_secrets.py --dry-run
    uv run python scripts/migrate_provider_secrets.py --apply
    uv run python scripts/migrate_provider_secrets.py --verify
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from app.core.crypto import (
    decrypt_secret,
    encrypt_secret,
    is_encrypted,
    mask_secret,
    reencrypt_secret,
)
from app.core.database import AsyncSessionFactory
from app.modules.modelops.models import ModelProviderConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("secret-migrator")


@dataclass
class KeyStats:
    total_providers: int = 0
    primary_encrypted: int = 0
    primary_plaintext: int = 0
    primary_empty: int = 0
    primary_corrupted: int = 0

    pool_keys_total: int = 0
    pool_keys_encrypted: int = 0
    pool_keys_plaintext: int = 0
    pool_keys_empty: int = 0
    pool_keys_corrupted: int = 0


async def inspect_secrets() -> tuple[KeyStats, list[dict[str, Any]]]:
    """Inspect all provider secrets and return detailed stats and provider inventory."""
    stats = KeyStats()
    providers_detail: list[dict[str, Any]] = []

    async with AsyncSessionFactory() as db:
        result = await db.execute(select(ModelProviderConfig).order_by(ModelProviderConfig.created_at))
        providers = list(result.scalars().all())

    stats.total_providers = len(providers)

    for p in providers:
        p_info: dict[str, Any] = {
            "id": p.id,
            "name": p.name,
            "provider_type": p.provider_type,
            "primary_status": "empty",
            "pool_keys": [],
        }

        # 1. Primary key check
        primary = p.api_key_encrypted
        if not primary or not primary.strip():
            stats.primary_empty += 1
            p_info["primary_status"] = "empty"
        elif is_encrypted(primary):
            decrypted = decrypt_secret(primary)
            if decrypted is None:
                stats.primary_corrupted += 1
                p_info["primary_status"] = "corrupted"
            else:
                stats.primary_encrypted += 1
                p_info["primary_status"] = "encrypted"
        else:
            stats.primary_plaintext += 1
            p_info["primary_status"] = "plaintext"

        # 2. Key pool check
        extra = p.extra_config or {}
        keys_list = extra.get("api_keys", [])
        for k_item in keys_list:
            stats.pool_keys_total += 1
            k_val = k_item.get("api_key")
            k_id = k_item.get("id", "unknown")
            if not k_val or not str(k_val).strip():
                stats.pool_keys_empty += 1
                p_info["pool_keys"].append({"id": k_id, "status": "empty"})
            elif is_encrypted(k_val):
                decrypted = decrypt_secret(k_val)
                if decrypted is None:
                    stats.pool_keys_corrupted += 1
                    p_info["pool_keys"].append({"id": k_id, "status": "corrupted"})
                else:
                    stats.pool_keys_encrypted += 1
                    p_info["pool_keys"].append({"id": k_id, "status": "encrypted"})
            else:
                stats.pool_keys_plaintext += 1
                p_info["pool_keys"].append({"id": k_id, "status": "plaintext"})

        providers_detail.append(p_info)

    return stats, providers_detail


def print_stats_table(stats: KeyStats, mode: str) -> None:
    """Print structured summary report without exposing secrets."""
    logger.info("=========================================================")
    logger.info(" PROVIDER SECRETS MIGRATION REPORT [%s]", mode.upper())
    logger.info("=========================================================")
    logger.info(" Total Providers:                %d", stats.total_providers)
    logger.info(" --- Primary API Keys ---")
    logger.info("   Encrypted (enc:v1:):          %d", stats.primary_encrypted)
    logger.info("   Plaintext (VULNERABLE):       %d", stats.primary_plaintext)
    logger.info("   Empty / None:                 %d", stats.primary_empty)
    logger.info("   Corrupted / Undecryptable:    %d", stats.primary_corrupted)
    logger.info(" --- Key Pool Keys ---")
    logger.info("   Total Pool Keys:              %d", stats.pool_keys_total)
    logger.info("   Encrypted (enc:v1:):          %d", stats.pool_keys_encrypted)
    logger.info("   Plaintext (VULNERABLE):       %d", stats.pool_keys_plaintext)
    logger.info("   Empty:                        %d", stats.pool_keys_empty)
    logger.info("   Corrupted / Undecryptable:    %d", stats.pool_keys_corrupted)
    logger.info("=========================================================")


async def run_dry_run() -> int:
    """Inspect secrets and report findings without modifying the database."""
    logger.info("Starting DRY-RUN mode (read-only audit)...")
    stats, providers_detail = await inspect_secrets()
    print_stats_table(stats, "DRY-RUN")

    for p in providers_detail:
        pool_plain = sum(1 for k in p["pool_keys"] if k["status"] == "plaintext")
        logger.info(
            "Provider [%s] '%s' (%s) -> Primary: %s | Pool keys: %d total (%d plaintext)",
            p["id"],
            p["name"],
            p["provider_type"],
            p["primary_status"],
            len(p["pool_keys"]),
            pool_plain,
        )

    if stats.primary_plaintext > 0 or stats.pool_keys_plaintext > 0:
        logger.warning(
            "Found %d plaintext primary keys and %d plaintext pool keys. Run with --apply to encrypt.",
            stats.primary_plaintext,
            stats.pool_keys_plaintext,
        )
    else:
        logger.info("All configured secrets are already properly encrypted.")
    return 0


async def run_apply() -> int:
    """Migrate all plaintext keys to encrypted tokens in a transactional batch."""
    logger.info("Starting APPLY mode (encrypting secrets in transaction)...")
    updated_providers = 0
    encrypted_primary_count = 0
    encrypted_pool_count = 0

    async with AsyncSessionFactory() as db:
        result = await db.execute(select(ModelProviderConfig))
        providers = list(result.scalars().all())

        for p in providers:
            modified = False

            # 1. Migrate primary key
            if p.api_key_encrypted and p.api_key_encrypted.strip():
                if not is_encrypted(p.api_key_encrypted):
                    # Plaintext -> Encrypt
                    p.api_key_encrypted = encrypt_secret(p.api_key_encrypted.strip())
                    encrypted_primary_count += 1
                    modified = True
                else:
                    # Already encrypted: attempt re-encryption for key rotation
                    re_enc = reencrypt_secret(p.api_key_encrypted)
                    if re_enc != p.api_key_encrypted:
                        p.api_key_encrypted = re_enc
                        modified = True

            # 2. Migrate key pool in extra_config
            extra = dict(p.extra_config) if p.extra_config else {}
            keys_list = extra.get("api_keys", [])
            pool_modified = False

            for k_item in keys_list:
                raw_k = k_item.get("api_key")
                if raw_k and str(raw_k).strip():
                    if not is_encrypted(raw_k):
                        enc = encrypt_secret(str(raw_k).strip())
                        k_item["api_key"] = enc
                        k_item["api_key_masked"] = mask_secret(raw_k)
                        encrypted_pool_count += 1
                        pool_modified = True
                    else:
                        re_enc = reencrypt_secret(raw_k)
                        if re_enc != raw_k:
                            k_item["api_key"] = re_enc
                            pool_modified = True

            if pool_modified:
                extra["api_keys"] = keys_list
                p.extra_config = extra
                flag_modified(p, "extra_config")
                modified = True

            if modified:
                updated_providers += 1
                logger.info(
                    "Encrypted secrets for Provider [%s] '%s' (%s)",
                    p.id,
                    p.name,
                    p.provider_type,
                )

        if updated_providers > 0:
            await db.commit()
            logger.info(
                "APPLY completed: committed changes for %d providers (%d primary keys, %d pool keys).",
                updated_providers,
                encrypted_primary_count,
                encrypted_pool_count,
            )
        else:
            logger.info("APPLY completed: No plaintext keys found to encrypt. Database is up to date.")

    # Post-apply inspection
    stats, _ = await inspect_secrets()
    print_stats_table(stats, "POST-APPLY")
    return 0


async def run_verify() -> int:
    """Verify that zero plaintext secrets remain and all ciphertexts decrypt properly."""
    logger.info("Starting VERIFY mode (validating encryption integrity)...")
    stats, providers_detail = await inspect_secrets()
    print_stats_table(stats, "VERIFY")

    errors: list[str] = []

    for p in providers_detail:
        if p["primary_status"] == "plaintext":
            errors.append(f"Provider [{p['id']}] '{p['name']}': primary key is in PLAINTEXT.")
        elif p["primary_status"] == "corrupted":
            errors.append(f"Provider [{p['id']}] '{p['name']}': primary key ciphertext cannot be decrypted.")

        for k in p["pool_keys"]:
            if k["status"] == "plaintext":
                errors.append(
                    f"Provider [{p['id']}] '{p['name']}': key pool item [{k['id']}] is in PLAINTEXT."
                )
            elif k["status"] == "corrupted":
                errors.append(
                    f"Provider [{p['id']}] '{p['name']}': key pool item [{k['id']}] cannot be decrypted."
                )

    if errors:
        logger.error("=========================================================")
        logger.error(" VERIFICATION FAILED: %d security violations found!", len(errors))
        for err in errors:
            logger.error("   - %s", err)
        logger.error("=========================================================")
        return 1

    logger.info("=========================================================")
    logger.info(" VERIFICATION PASSED: 100% of provider secrets are encrypted.")
    logger.info(" Zero plaintext secrets found. All ciphertexts decrypt successfully.")
    logger.info("=========================================================")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="QNU AI Platform — Provider Secrets Migration Tool",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect database secrets and report findings without changing anything.",
    )
    group.add_argument(
        "--apply",
        action="store_true",
        help="Encrypt all plaintext secrets in a database transaction.",
    )
    group.add_argument(
        "--verify",
        action="store_true",
        help="Validate that zero plaintext secrets exist and all ciphertexts are decryptable.",
    )

    args = parser.parse_args()

    if args.dry_run:
        return asyncio.run(run_dry_run())
    if args.apply:
        return asyncio.run(run_apply())
    if args.verify:
        return asyncio.run(run_verify())
    return 1


if __name__ == "__main__":
    sys.exit(main())
