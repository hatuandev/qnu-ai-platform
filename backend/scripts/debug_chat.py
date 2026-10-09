import asyncio
import json
from pathlib import Path

from app.core.database import AsyncSessionFactory
from app.modules.assistants.schemas import AssistantChatRequest
from app.modules.assistants.service import assistant_service


async def main():
    async with AsyncSessionFactory() as db:
        req = AssistantChatRequest(
            message="Năm 2026 trường Đại học Quy Nhơn dự kiến tuyển sinh bao nhiêu chỉ tiêu và áp dụng những phương thức xét tuyển nào?",
            tenant_id="tenant_qnu",
            stream=False
        )
        resp = await assistant_service.chat(db, "ast_admissions", req)
        content = json.dumps(resp.model_dump(mode="json"), indent=2, ensure_ascii=False)
        await asyncio.to_thread(Path("chat_response_debug.json").write_text, content, encoding="utf-8")
        print("Chat response saved to chat_response_debug.json")

if __name__ == '__main__':
    asyncio.run(main())
