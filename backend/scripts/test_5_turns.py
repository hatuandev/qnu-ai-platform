import asyncio
import json
from pathlib import Path

from app.core.database import AsyncSessionFactory
from app.modules.assistants.schemas import AssistantChatRequest
from app.modules.assistants.service import assistant_service


async def main():
    async with AsyncSessionFactory() as db:
        conv_id = "test_conv_admissions_3turns"
        questions = [
            "Năm 2026 trường Đại học Quy Nhơn dự kiến tuyển sinh bao nhiêu chỉ tiêu và áp dụng những phương thức xét tuyển nào?",
            "Thí sinh có chứng chỉ IELTS 6.5 hoặc chứng chỉ tiếng Anh VSTEP 6.0 (B2) thì được quy đổi thành bao nhiêu điểm môn Tiếng Anh khi xét tuyển đại học năm 2026?",
            "Mức học phí dự kiến toàn khóa đối với các ngành đào tạo Kỹ sư hệ chính quy năm 2026 tại Trường Đại học Quy Nhơn là bao nhiêu?",
            "Theo Quyết định số 2327/QĐ-ĐHQN, trường Đại học Quy Nhơn đã bổ nhiệm ông Nguyễn Đức Tôn giữ chức vụ gì và thời hạn bổ nhiệm là bao lâu?",
            "Điểm chuẩn trúng tuyển ngành Y đa khoa (Bác sĩ đa khoa) năm 2025 của Trường Đại học Quy Nhơn là bao nhiêu và ngành này xét tổ hợp môn nào?"
        ]
        
        results = []
        for idx, q in enumerate(questions, 1):
            print(f"Executing turn {idx}...")
            req = AssistantChatRequest(
                message=q,
                conversation_id=conv_id,
                tenant_id="tenant_qnu",
                stream=False
            )
            resp = await assistant_service.chat(db, "ast_admissions", req)
            print(f"Turn {idx} completed: status={resp.status}, citations={len(resp.citations)}")
            results.append({
                "turn": idx,
                "question": q,
                "status": resp.status,
                "citations_count": len(resp.citations),
                "citations": [c if isinstance(c, dict) else c.model_dump() for c in resp.citations],
                "answer": resp.answer
            })
            
        content = json.dumps(results, indent=2, ensure_ascii=False)
        await asyncio.to_thread(Path("multi_turn_test_results.json").write_text, content, encoding="utf-8")
        print("\nAll 5 questions completed and saved to multi_turn_test_results.json")

if __name__ == '__main__':
    asyncio.run(main())
