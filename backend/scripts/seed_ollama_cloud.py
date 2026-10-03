"""Seed script to populate Ollama Cloud provider and its API key pool in PostgreSQL database."""

from __future__ import annotations

import asyncio
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

# UTF-8 for console output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import select

from app.core.crypto import encrypt_secret
from app.core.database import AsyncSessionFactory
from app.modules.modelops.models import ModelProviderConfig, ProviderApiKey
from app.modules.modelops.services.provider_service import mask_api_key

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_ollama_cloud")

OLLAMA_RAW_KEYS = [
    {
        "id": "c82209d6-57f8-49f9-bb5c-15251e1a36e0",
        "name": "anhtuan1991qn",
        "api_key": "9548f63c5f734183be69cf224f7ade63.ybXnOyUb19xyiBahhHmRMnZa",
        "priority": 1,
        "is_active": True,
    },
    {
        "id": "aacbe125-955b-4de4-b0b1-e27fdd0e2cfc",
        "name": "hoanhtuan",
        "api_key": "b80be69779a0477880a5d7804f8a11f5.ppK4sNXca9IeEauMphLSB-fg",
        "priority": 2,
        "is_active": True,
    },
    {
        "id": "21aae112-4065-4159-ae1c-d6c25c95d66c",
        "name": "anhtuandev",
        "api_key": "c4cccdf41240409abde92c2f75fa8021.LPBwqRBNiJwxMoFncJxc6hrO",
        "priority": 3,
        "is_active": True,
    },
    {
        "id": "0d43b357-f5a7-4581-beea-d57c7d942830",
        "name": "anhtuandev2",
        "api_key": "7eec42d9d1294048a1f6fd074e453515.Ni_5Si71fdu9jTINthn_TQDz",
        "priority": 4,
        "is_active": True,
    },
    {
        "id": "2389973b-c4dd-40dc-b04c-c271b85cddcc",
        "name": "anhtuandev3",
        "api_key": "0fbbcb63689148a3a0d58b73761d6255.xGCnpfjds-DKlyfdqEWDCH9Y",
        "priority": 5,
        "is_active": True,
    },
    {
        "id": "e36696ef-ad0c-4356-8a90-668a47b71ad5",
        "name": "dev5",
        "api_key": "0bafa2459e06441db588e9e295e0ebc9.gv99otGHCIplqMk0J_46B9oj",
        "priority": 6,
        "is_active": True,
    },
    {
        "id": "82f7d534-c88a-443c-b031-f24d4ad10e41",
        "name": "dev7",
        "api_key": "197d874f9e544296b48c07c230a43923.UXyIzKuztJJyi9ETEAxTJhaN",
        "priority": 7,
        "is_active": True,
    },
    {
        "id": "343b4280-615f-41f7-8625-852e98d46f02",
        "name": "hatuan1991",
        "api_key": "6d5250053b18447497b826dc8213395b.9EGY0Z-8_JjFpOEI2dKwOCky",
        "priority": 8,
        "is_active": True,
    },
    {
        "id": "4cc48562-d88c-4005-a78e-9d3e07f01641",
        "name": "a7",
        "api_key": "36fb037abc434c38b18c61da431ae11e.FjJb4sk05813UaYYN-e4dwny",
        "priority": 9,
        "is_active": True,
    },
    {
        "id": "68984baf-4a17-4ad8-8d61-501ccef585f8",
        "name": "ngoc",
        "api_key": "20273e1d029a4592b1b5c680f77e05e1.SRBmwTA7GDw9EsqBuBL7TowZ",
        "priority": 10,
        "is_active": True,
    },
    {
        "id": "bfef3f33-331d-4072-8282-86bfecb23cd3",
        "name": "bao",
        "api_key": "4d8cebf58e0a4d8fa3d74f0b4be706f8.jKF7KrIZmFomXAa6WFnDVf0A",
        "priority": 11,
        "is_active": True,
    },
    {
        "id": "5a33a492-fb81-45be-813e-554a67ad240f",
        "name": "dvtuan",
        "api_key": "6b3a210e939e48f99871dc496a1fd60f.yaQYsxE56VPaWjehNq_uAWpS",
        "priority": 12,
        "is_active": True,
    },
    {
        "id": "7087495f-ba62-41ef-bb3f-f686e6160b2c",
        "name": "nguyen thi",
        "api_key": "51057b0212f1483b9fd219acba006f05.MDSLevSxhLZwRHd_s9z7rQ-6",
        "priority": 13,
        "is_active": True,
    },
    {
        "id": "5a591fe1-a612-412e-99f3-74113111d806",
        "name": "thanh truc",
        "api_key": "56c9ade8e8ec4a15b5006c663643592d.p8VIWBFJLpXTQtHt7FWWhZmC",
        "priority": 14,
        "is_active": True,
    },
    {
        "id": "a576c87d-4db8-4388-aaaf-64987636e42a",
        "name": "anh nang",
        "api_key": "9cee6ce35ce54a64af0a3168e524bd7f.-eclDcBFxYDlNLE8EhtRXB87",
        "priority": 15,
        "is_active": True,
    },
    {
        "id": "92788e15-3ee1-4e36-8835-bfd2f5d206dc",
        "name": "truc 2",
        "api_key": "1b3882ac47bb4b028f251fa1c7fd6a85.vZw0IHcrGY5QzJQWt2BepIKJ",
        "priority": 16,
        "is_active": True,
    },
    {
        "id": "adb64911-87aa-4d82-aaa8-8957fa676f4f",
        "name": "thi 2",
        "api_key": "426afdb7adbe45318a31ee71dc12c704.y8K2E4va1ZV0S2KkfJ6Qsw9x",
        "priority": 17,
        "is_active": True,
    },
    {
        "id": "0fdbb559-92c0-418f-9e19-124533140cc3",
        "name": "chi thom",
        "api_key": "4d91f313c00c43fca588f94df48288df.qH7pNGV36dtvNUPgmEpY6NCK",
        "priority": 18,
        "is_active": True,
    },
    {
        "id": "a2b0224d-f7b5-4713-b6f1-ef94c71bd7f1",
        "name": "chi phuong",
        "api_key": "db96dc779a6d4623a91dbc045838af82.6N-f5EDlp6hVw_1G1GIbM3xt",
        "priority": 19,
        "is_active": True,
    },
    {
        "id": "9359c40c-27ae-45cd-8d34-adbdec0f439c",
        "name": "chi hang 1",
        "api_key": "1d679d0c960740c7a354303d49c83ed7.VjfTeQmqeksTPjNiuNSgVouD",
        "priority": 20,
        "is_active": False,
    },
    {
        "id": "ce432709-0a87-41dc-908d-2e6f8be34555",
        "name": "chi hang 2",
        "api_key": "fb9e992e1ea54841b7bc3afa8789d202.-cnEEtKplz6p5dq8OozLPt1B",
        "priority": 21,
        "is_active": False,
    },
    {
        "id": "35cdc6fa-207f-44d6-a1d9-f395c20f00b1",
        "name": "chi hang 3",
        "api_key": "c53b2027c89e4f4bac502f6d651da685.0B5hQv6krTlaFWW6Gqs3euPc",
        "priority": 22,
        "is_active": False,
    },
    {
        "id": "48c6f260-1751-401f-806a-2139818e76fa",
        "name": "hien 1",
        "api_key": "20b9024948d84a64a060f043705b23ec.IJ3tnJKfZouleWqKnwUJgzC1",
        "priority": 23,
        "is_active": False,
    },
    {
        "id": "d4bdc74f-1f69-4010-8cb5-291271a7d840",
        "name": "thuan 1",
        "api_key": "857e795221a54c438297cfb8d64442e4.vlh1-ud0NLp9rwgqcU6CBiLl",
        "priority": 24,
        "is_active": False,
    },
    {
        "id": "874daf54-33c0-4549-8089-eafa1d4593df",
        "name": "thuan 2",
        "api_key": "1bb61d8722ac49a2b0118ec8792509e4.o4pzozVWT_f9wTYgo3G5APBo",
        "priority": 25,
        "is_active": False,
    },
]

OLLAMA_CLOUD_MODELS = [
    "gpt-oss:120b",
    "gemma4:31b",
    "nemotron-3-super",
    "nemotron-3-ultra",
    "nemotron-3-nano:30b",
]


async def seed_ollama_cloud_provider() -> None:
    """Seed Ollama Cloud provider config and 25 API keys into PostgreSQL."""
    logger.info("Connecting to PostgreSQL to seed Ollama Cloud...")

    async with AsyncSessionFactory() as db:
        # 1. Check or create ModelProviderConfig for Ollama Cloud
        provider_id = "prov_ollama_cloud"
        res = await db.execute(select(ModelProviderConfig).where(ModelProviderConfig.id == provider_id))
        provider = res.scalar_one_or_none()

        extra_config = {
            "models": OLLAMA_CLOUD_MODELS,
            "api_keys": [],
        }

        # Use primary key from first active credential
        first_active_key = OLLAMA_RAW_KEYS[0]["api_key"]
        encrypted_primary = encrypt_secret(first_active_key)

        if provider is None:
            logger.info("Creating new ModelProviderConfig: %s", provider_id)
            provider = ModelProviderConfig(
                id=provider_id,
                name="Ollama Cloud",
                provider_type="ollama_cloud",
                model_name="gpt-oss:120b",
                api_base_url="https://ollama.com/v1",
                api_key_encrypted=encrypted_primary,
                priority=8,
                is_active=True,
                timeout_seconds=30,
                extra_config=extra_config,
            )
            db.add(provider)
            await db.flush()
        else:
            logger.info("Updating existing ModelProviderConfig: %s", provider_id)
            provider.name = "Ollama Cloud"
            provider.provider_type = "ollama_cloud"
            provider.api_base_url = "https://ollama.com/v1"
            provider.model_name = "gpt-oss:120b"
            provider.api_key_encrypted = encrypted_primary
            provider.is_active = True
            provider.extra_config = {
                **(provider.extra_config or {}),
                "models": OLLAMA_CLOUD_MODELS,
            }

        # 2. Seed all 25 ProviderApiKey rows
        now = datetime.now(UTC)
        seeded_count = 0
        active_count = 0
        keys_for_extra = []

        for item in OLLAMA_RAW_KEYS:
            key_id = item["id"]
            encrypted_secret = encrypt_secret(item["api_key"])
            masked_key = mask_api_key(item["api_key"])
            display_name = f"Ollama Cloud - {item['name']}"
            is_active = item["is_active"]
            priority = item["priority"]
            status = "active" if is_active else "inactive"

            # Check if row exists
            k_res = await db.execute(
                select(ProviderApiKey).where(
                    ProviderApiKey.id == key_id,
                    ProviderApiKey.provider_id == provider_id,
                )
            )
            existing_key = k_res.scalar_one_or_none()

            if existing_key is None:
                new_key_row = ProviderApiKey(
                    id=key_id,
                    provider_id=provider_id,
                    name=display_name,
                    api_key_encrypted=encrypted_secret,
                    api_key_masked=masked_key,
                    account_id=None,
                    priority=priority,
                    is_active=is_active,
                    status=status,
                    quota_limit=None,
                    usage_tokens=0,
                    consecutive_failures=0,
                    created_at=now,
                    updated_at=now,
                )
                db.add(new_key_row)
            else:
                existing_key.name = display_name
                existing_key.api_key_encrypted = encrypted_secret
                existing_key.api_key_masked = masked_key
                existing_key.priority = priority
                existing_key.is_active = is_active
                existing_key.status = status
                existing_key.updated_at = now

            seeded_count += 1
            if is_active:
                active_count += 1

            keys_for_extra.append({
                "id": key_id,
                "name": display_name,
                "api_key": encrypted_secret,
                "api_key_masked": masked_key,
                "priority": priority,
                "is_active": is_active,
                "status": status,
                "quota_limit": None,
                "usage_tokens": 0,
                "cooldown_until": None,
                "last_used_at": None,
                "created_at": now.isoformat(),
            })

        # Synchronize provider extra_config api_keys
        provider.extra_config = {
            **(provider.extra_config or {}),
            "api_keys": keys_for_extra,
        }

        await db.commit()
        logger.info(
            "SUCCESS: Seeded Ollama Cloud provider '%s' with %d API keys (%d active, %d inactive).",
            provider_id,
            seeded_count,
            active_count,
            seeded_count - active_count,
        )


if __name__ == "__main__":
    asyncio.run(seed_ollama_cloud_provider())
