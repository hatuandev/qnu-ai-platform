import asyncio
import sys

from sqlalchemy import text

from app.core.crypto import decrypt_secret
from app.core.database import AsyncSessionFactory
from app.modules.modelops.providers.gemini_adapter import GeminiAdapter
from app.modules.modelops.schemas import ChatMessage

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

async def test_both_keys_adapter():
    async with AsyncSessionFactory() as db:
        r = await db.execute(text("SELECT extra_config FROM model_provider_configs WHERE id = 'prov_gemini'"))
        cfg = r.scalar()
        keys = cfg.get("api_keys", [])
        
        messages = [
            ChatMessage(role="user", content="Chào bạn, hãy trả lời bằng đúng 2 từ: 'Hoàn thành'"),
        ]
        
        for idx, k in enumerate(keys):
            decrypted = decrypt_secret(k.get("api_key", ""))
            print("\n==========================================")
            print(f"Testing GeminiAdapter with Key #{idx} [{k.get('name')}]:")
            adapter = GeminiAdapter(
                model_name="gemini-2.5-flash",
                api_key=decrypted,
                timeout_seconds=15.0,
            )
            try:
                resp = await adapter.generate(messages)
                print("  -> SUCCESS!")
                print(f"  -> Model used: {resp.model}")
                print(f"  -> Latency: {resp.latency_ms} ms")
                print(f"  -> Content: {resp.content.strip()}")
            except Exception as exc:
                print(f"  -> FAILED: {exc}")

if __name__ == "__main__":
    asyncio.run(test_both_keys_adapter())
