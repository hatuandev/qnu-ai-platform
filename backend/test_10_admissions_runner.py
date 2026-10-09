"""Automated Test Runner for the 10 Admissions Questions against QNU AI Platform Admissions Assistant."""

import asyncio
import json
import sys
import time
from pathlib import Path

# Ensure UTF-8 output encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from app.core.database import AsyncSessionFactory
from app.modules.assistants.schemas import AssistantChatRequest
from app.modules.assistants.services.assistant_chat_service import AssistantChatService
from app.modules.modelops.circuit_breaker import circuit_breaker_registry

QUESTIONS = [
    {
        "id": 1,
        "question": "Năm 2026, Trường Đại học Quy Nhơn tuyển sinh theo những phương thức nào và tổng chỉ tiêu dự kiến là bao nhiêu?",
        "expected_topics": ["5 phương thức (PT1..PT5) + xét tuyển thẳng", "4800 chỉ tiêu dự kiến"]
    },
    {
        "id": 2,
        "question": "Em muốn xét tuyển vào các ngành Sư phạm (đào tạo giáo viên) bằng điểm học bạ THPT hoặc điểm Đánh giá năng lực ĐHQG TP.HCM có được không?",
        "expected_topics": ["KHÔNG được xét tuyển", "Các ngành đào tạo giáo viên không xét tuyển PT2 (học bạ) và PT3 (ĐGNL ĐHQG TP.HCM)"]
    },
    {
        "id": 3,
        "question": "Điểm chuẩn trúng tuyển theo phương thức Học bạ (PT2) của các ngành Quản trị kinh doanh, Kinh tế, và Kế toán năm 2026 là bao nhiêu?",
        "expected_topics": ["Điểm chuẩn học bạ 2026 của Quản trị kinh doanh, Kinh tế, Kế toán từ văn bản điểm chuẩn/quy đổi"]
    },
    {
        "id": 4,
        "question": "Điểm chuẩn theo kỳ thi Đánh giá năng lực của ĐH Sư phạm Hà Nội (PT4) của ngành Sư phạm Toán học và Giáo dục Tiểu học là bao nhiêu?",
        "expected_topics": ["Điểm chuẩn PT4 ĐGNL ĐH Sư phạm Hà Nội"]
    },
    {
        "id": 5,
        "question": "Em có chứng chỉ IELTS 5.5 (hoặc VSTEP Bậc 4) thì khi xét tuyển vào QNU bằng PT1 hoặc PT2, môn Tiếng Anh được quy đổi sang bao nhiêu điểm?",
        "expected_topics": ["IELTS 5.5 -> 8.5 điểm", "VSTEP Bậc 4 (4.0) -> 8.0 điểm"]
    },
    {
        "id": 6,
        "question": "Tổ hợp môn X26 (Toán, Tin học, Tiếng Anh) và X78 (Ngữ văn, Giáo dục KT và PL, Tiếng Anh) được quy về tổ hợp gốc nào theo quy định của trường?",
        "expected_topics": ["X26 -> A01", "X78 -> D01"]
    },
    {
        "id": 7,
        "question": "Nếu em đạt giải Ba trong kỳ thi chọn Học sinh giỏi quốc gia thì được cộng bao nhiêu điểm ưu tiên xét tuyển?",
        "expected_topics": ["Giải Ba HSG quốc gia -> cộng 1.0 điểm", "Thời hạn giải không quá 3 năm"]
    },
    {
        "id": 8,
        "question": "Ngành Giáo dục Mầm non (mã 7140201) tuyển sinh theo phương thức nào và tổ hợp môn thi gồm những gì?",
        "expected_topics": ["Phương thức 5 (PT5 - mã 405)", "Tổ hợp: Văn, Toán, Năng khiếu GDMN"]
    },
    {
        "id": 9,
        "question": "Điểm thi tốt nghiệp THPT của em tổ hợp D01 được 21.0 điểm. Em muốn học các ngành khối Kinh tế hoặc Công nghệ tại QNU thì cơ hội trúng tuyển thế nào?",
        "expected_topics": ["Tư vấn cơ hội trúng tuyển dựa trên phổ điểm 2024/2025 các ngành Kinh tế / Công nghệ"]
    },
    {
        "id": 10,
        "question": "Điểm chuẩn trúng tuyển ngành Trí tuệ nhân tạo của Trường Đại học Quy Nhơn năm 2028 là bao nhiêu điểm?",
        "expected_topics": ["Năm tương lai 2028: Chưa có dữ liệu / Chưa diễn ra", "Cung cấp điểm chuẩn 2024/2025 hoặc hướng dẫn theo dõi"]
    }
]

from app.core.redis import get_redis_client
from app.modules.modelops.circuit_breaker import CircuitBreakerState


async def run_all_tests():
    # Clear old RAG cache in Redis
    try:
        r_client = get_redis_client()
        keys = await r_client.keys("rag:cache:*")
        if keys:
            await r_client.delete(*keys)
            print(f" Đã dọn dẹp {len(keys)} bản ghi cache cũ trong Redis.")
        await r_client.aclose()
    except Exception as r_err:
        print(f"Lưu ý kết nối Redis: {r_err}")

    # Reset circuit breakers
    for name in ["Google Gemini", "gemini", "prov_gemini", "cloudflare", "groq"]:
        cb = circuit_breaker_registry.get(name)
        cb.state = CircuitBreakerState.CLOSED
        cb.failure_count = 0
        cb.last_failure_time = 0

    results = []
    print("=" * 80)
    print("BẮT ĐẦU KIỂM THỬ 10 CÂU HỎI TUYỂN SINH TRÊN ADMISSIONS ASSISTANT")
    print("=" * 80)

    async with AsyncSessionFactory() as db:
        chat_svc = AssistantChatService()
        
        for item in QUESTIONS:
            q_id = item["id"]
            q_text = item["question"]
            print(f"\n[CÂU HỎI {q_id}/10]: {q_text}")
            start_t = time.time()
            
            try:
                # Use unique conversation ID for each question to test independent retrieval and grounded answer
                req = AssistantChatRequest(
                    message=q_text,
                    tenant_id="tenant_qnu",
                    conversation_id=f"test_eval_q{q_id}_{int(time.time())}"
                )
                res = await chat_svc.chat(db, reference="admissions", request=req)
                elapsed = round(time.time() - start_t, 2)
                
                citations_summary = []
                for c in (res.citations or []):
                    title = c.get("title") or c.get("document_name") or "Tài liệu"
                    page = c.get("page_number") or c.get("page")
                    citations_summary.append(f"{title} (Trang {page})")

                result_entry = {
                    "id": q_id,
                    "question": q_text,
                    "elapsed_sec": elapsed,
                    "status": res.status,
                    "answer": res.answer,
                    "citations_count": len(res.citations or []),
                    "citations": citations_summary[:5],
                    "expected_topics": item["expected_topics"],
                    "artifacts_count": len(res.artifacts or [])
                }
                results.append(result_entry)
                
                print(f"-> Thời gian: {elapsed}s | Số trích dẫn: {len(res.citations or [])}")
                print(f"-> Câu trả lời (trích 250 ký tự đầu):\n{res.answer[:250]}...\n")
                
            except Exception as exc:
                elapsed = round(time.time() - start_t, 2)
                print(f"-> LỖI: {type(exc).__name__}: {exc}")
                results.append({
                    "id": q_id,
                    "question": q_text,
                    "elapsed_sec": elapsed,
                    "status": "error",
                    "answer": f"Error: {exc}",
                    "citations_count": 0,
                    "expected_topics": item["expected_topics"]
                })

    # Save results to json
    output_path = "test_10_admissions_results.json"
    content = json.dumps(results, ensure_ascii=False, indent=2)
    await asyncio.to_thread(Path(output_path).write_text, content, encoding="utf-8")
    print(f"\n ĐÃ LƯU KẾT QUẢ ĐẦY ĐỦ VÀO: {output_path}")

if __name__ == "__main__":
    asyncio.run(run_all_tests())
