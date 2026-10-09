import asyncio

from app.core.database import AsyncSessionFactory
from app.modules.rag.schemas import AskRequest
from app.modules.rag.service import rag_service


async def main():
    async with AsyncSessionFactory() as db:
        query = "Căn cứ Quyết định số 2327/QĐ-ĐHQN, trường Đại học Quy Nhơn bổ nhiệm TS Nguyễn Đức Tôn giữ chức vụ gì và thời hạn bao nhiêu năm?"
        ask_req = AskRequest(
            question=query,
            collection_id="col_admissions",
            module_code="admissions",
            preferred_model_name="gemini-3.5-flash-lite",
            tenant_id="tenant_qnu",
        )
        res = await rag_service.ask(db, ask_req)
        print("=== RESULT ===")
        print("Status:", res.status)
        print("Citations count:", len(res.citations))
        for c in res.citations:
            print(f"- Source: {c.source_id} | Title: {c.title}")
            print(f"  Quote: {c.quote[:100]}...")
        print("Answer:\n", res.answer)

if __name__ == '__main__':
    asyncio.run(main())
