import asyncio
import sys

from app.core.database import AsyncSessionFactory
from app.modules.modelops.schemas import ChatMessage, LLMGenerateRequest
from app.modules.modelops.services.inference_service import inference_service

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

async def test_rotation():
    async with AsyncSessionFactory() as db:
        print("Testing 2 calls via InferenceService to observe key usage / rotation...")
        for i in range(2):
            req = LLMGenerateRequest(
                messages=[ChatMessage(role="user", content=f"Tin nhắn kiểm tra số {i+1}, hãy đáp 'OK {i+1}'")],
                preferred_provider_id="prov_gemini",
                preferred_model_name="gemini-2.5-flash",
                tenant_id="tenant_qnu_default",
            )
            resp = await inference_service.generate(db, req)
            print(f"Call #{i+1}:")
            print(f"  Provider: {resp.provider}")
            print(f"  Model: {resp.model}")
            print(f"  Active Key ID used: {resp.active_key_id}")
            print(f"  Content: {resp.content.strip()}")
            print(f"  Latency: {resp.latency_ms} ms")

if __name__ == "__main__":
    asyncio.run(test_rotation())
