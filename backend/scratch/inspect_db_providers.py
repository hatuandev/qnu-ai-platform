import asyncio
import sys
from app.core.database import AsyncSessionFactory
from sqlalchemy import text

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

async def inspect():
    async with AsyncSessionFactory() as db:
        r = await db.execute(text("SELECT id, name, provider_type, api_key_encrypted, extra_config FROM model_provider_configs"))
        rows = r.fetchall()
        print(f"Total providers in DB: {len(rows)}")
        for row in rows:
            p_id, name, p_type, key_enc, extra = row
            keys = (extra or {}).get("api_keys", [])
            print(f"ID: {p_id:20} | Name: {name:20} | Type: {p_type:10} | Key Enc: {bool(key_enc)} | Keys count: {len(keys)}")
            for ki in keys:
                print(f"   -> Key: {ki.get('name')} | Masked: {ki.get('api_key_masked')} | Active: {ki.get('is_active')}")

if __name__ == "__main__":
    asyncio.run(inspect())
