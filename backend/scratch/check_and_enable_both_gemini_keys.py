import asyncio
import json
import sys
from sqlalchemy import text
from app.core.database import AsyncSessionFactory
from app.core.crypto import decrypt_secret

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

async def inspect_and_enable_keys():
    async with AsyncSessionFactory() as db:
        r = await db.execute(text("SELECT id, name, model_name, extra_config FROM model_provider_configs WHERE id = 'prov_gemini'"))
        row = r.fetchone()
        if not row:
            print("prov_gemini not found!")
            return
        
        cfg = row.extra_config or {}
        keys = cfg.get("api_keys", [])
        print(f"Provider: {row.name}, Model: {row.model_name}")
        print(f"Total keys configured: {len(keys)}")
        
        for i, k in enumerate(keys):
            raw_encrypted = k.get("api_key", "")
            decrypted = decrypt_secret(raw_encrypted) if raw_encrypted else ""
            print(f"\n--- Key #{i} ---")
            print(f"  Name: {k.get('name')}")
            print(f"  Active: {k.get('is_active')}, Status: {k.get('status')}")
            print(f"  Priority: {k.get('priority')}, Usage Tokens: {k.get('usage_tokens')}")
            print(f"  Cooldown until: {k.get('cooldown_until')}")
            print(f"  Key Prefix: {decrypted[:10]}... (len {len(decrypted)})")
            
            # Make sure both keys are active and out of cooldown
            k["is_active"] = True
            k["status"] = "active"
            k["cooldown_until"] = None
        
        cfg["api_keys"] = keys
        await db.execute(
            text("UPDATE model_provider_configs SET extra_config = :cfg WHERE id = 'prov_gemini'"),
            {"cfg": json.dumps(cfg)}
        )
        await db.commit()
        print("\n[OK] Both keys set to is_active=True, status='active' in database!")

if __name__ == "__main__":
    asyncio.run(inspect_and_enable_keys())
