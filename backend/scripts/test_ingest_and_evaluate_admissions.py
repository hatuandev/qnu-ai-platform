"""Script ingest 2 tệp tài liệu và kiểm thử quy trình DAG Trợ lý ảo Tư vấn Tuyển sinh (Bản tối ưu độc lập Session)."""

import asyncio
import os
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.core.database import AsyncSessionFactory
from app.modules.assistants.schemas import AssistantChatRequest
from app.modules.assistants.services.assistant_chat_service import AssistantChatService
from app.modules.knowledge.service import knowledge_service

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
COLLECTION_ID = "col_admissions"

FILES_TO_INGEST = [
    {
        "file_name": "Thong_bao_tuyen_sinh_dai_hoc_2026_cap_nhat.docx",
        "title": "Thông báo Thông tin Tuyển sinh Đại học năm 2026 (Cập nhật)",
        "doc_type": "thong_bao",
    },
    {
        "file_name": "Quyet_dinh_2327_QD_DHQN_bo_nhiem_can_bo.docx",
        "title": "Quyết định 2327/QĐ-ĐHQN về việc bổ nhiệm viên chức quản lý",
        "doc_type": "quyet_dinh",
    },
]

TEST_QUERIES = [
    {
        "id": "TC-01",
        "category": "Greeting Intent (Nhánh Chào hỏi)",
        "question": "Xin chào bạn, bạn là ai và có thể giúp gì cho mình?",
        "expected_branch": "condition_route -> greeting_llm -> greeting_output",
        "ground_truth_criteria": "Phản hồi tự nhiên, giới thiệu Trợ lý Tuyển sinh QNU, không tốn tài nguyên RAG, văn phong ấm áp.",
    },
    {
        "id": "TC-02",
        "category": "Core Admission Stats (Chỉ tiêu & Phương thức)",
        "question": "Tổng chỉ tiêu tuyển sinh đại học năm 2026 của Trường Đại học Quy Nhơn là bao nhiêu và có những phương thức xét tuyển nào?",
        "expected_branch": "query_rewrite -> knowledge_answer -> citation_guard -> chat_output",
        "ground_truth_criteria": "Tổng chỉ tiêu: 4800. Gồm 5 phương thức: PT1 (mã 100 - THPT), PT2 (mã 200 - Học bạ 3 năm), PT3 (mã 402A - ĐGNL ĐHQG TP.HCM), PT4 (mã 402B - ĐGNL ĐHSP Hà Nội), PT5 (mã 405 - Năng khiếu GDMN/GDTC) và Xét tuyển thẳng.",
    },
    {
        "id": "TC-03",
        "category": "Entity & Subject Group (Ngành cụ thể & Tổ hợp môn - Có lỗi Telex)",
        "question": "Ngay cong nghe thong tin xet tuyen nhung to hop mon nao vay ban?",
        "expected_branch": "query_rewrite (sửa 'ngay' -> 'ngành') -> knowledge_answer -> citation_guard -> chat_output",
        "ground_truth_criteria": "Mã ngành 7480201. Tổ hợp: (Toán, Anh, Lý), (Toán, Anh, Văn), (Toán, Anh, Hóa), (Toán, Anh, GD KT&PL), (Toán, Anh, Tin).",
    },
    {
        "id": "TC-04",
        "category": "Certificate Conversion (Quy đổi IELTS / VSTEP)",
        "question": "Mình có chứng chỉ IELTS 6.5 và bạn mình có VSTEP 6.0 thì được quy đổi thành bao nhiêu điểm môn Tiếng Anh khi xét tuyển?",
        "expected_branch": "knowledge_answer -> citation_guard -> chat_output",
        "ground_truth_criteria": "IELTS 6.5 quy đổi thành 9.5 điểm; VSTEP 6.0 quy đổi thành 9.0 điểm môn Tiếng Anh (PT1 và PT2).",
    },
    {
        "id": "TC-05",
        "category": "Tuition Policy (Học phí dự kiến)",
        "question": "Mức học phí toàn khóa dự kiến của các ngành cử nhân và kỹ sư đại trà là bao nhiêu?",
        "expected_branch": "knowledge_answer -> citation_guard -> chat_output",
        "ground_truth_criteria": "Cử nhân đại trà: 83 - 97 triệu đồng (khóa 4 năm); Kỹ sư đại trà: 112,3 triệu đồng (khóa 4,5 năm).",
    },
    {
        "id": "TC-06",
        "category": "Cross-Document / Administrative Boundary (Quyết định bổ nhiệm TS. Tôn)",
        "question": "Tiến sĩ Nguyễn Đức Tôn vừa được bổ nhiệm giữ chức vụ gì theo Quyết định 2327/QĐ-ĐHQN?",
        "expected_branch": "knowledge_answer / citation_guard / scope guard",
        "ground_truth_criteria": "Trợ lý Tuyển sinh xác định thông tin không thuộc phạm vi tuyển sinh hoặc trích dẫn từ chối lịch sự.",
    },
    {
        "id": "TC-07",
        "category": "Anti-Hallucination & No-Answer Policy (Ngành không đào tạo / Bẫy)",
        "question": "Điểm chuẩn ngành Y đa khoa của Trường Đại học Quy Nhơn năm 2025 là bao nhiêu?",
        "expected_branch": "knowledge_answer -> citation_guard (ungrounded) -> no_answer_output",
        "ground_truth_criteria": "Kích hoạt No-Answer Policy vì trường không đào tạo ngành Y đa khoa; không tự bịa điểm; hướng dẫn hotline 0256.3846.156.",
    },
]


async def step_ingest_documents():
    print("=" * 70)
    print("BƯỚC 1: KIỂM TRA & NẠP (INGEST) TÀI LIỆU VÀO KHO TRI THỨC col_admissions")
    print("=" * 70)

    for file_info in FILES_TO_INGEST:
        file_path = os.path.join(DATA_DIR, file_info["file_name"])
        if not os.path.exists(file_path):
            print(f"[!] File không tồn tại: {file_path}")
            continue

        file_bytes = await asyncio.to_thread(Path(file_path).read_bytes)

        print(f"\n[+] Đang xử lý tệp: {file_info['file_name']} ({len(file_bytes)} bytes)...")
        async with AsyncSessionFactory() as session:
            try:
                doc = await knowledge_service.ingest_document(
                    db=session,
                    collection_id=COLLECTION_ID,
                    file_bytes=file_bytes,
                    file_name=file_info["file_name"],
                    title=file_info["title"],
                    document_type_code=file_info.get("doc_type"),
                    auto_approve=True,
                )
                print(f"    -> ĐÃ NẠP MỚI THÀNH CÔNG: Doc ID = {doc.id}")
                print(f"    -> Trạng thái: status={doc.status}, index_status={doc.index_status}")
            except Exception as exc:
                print(f"    -> Ghi nhận: {exc}")


async def step_test_dag_queries():
    print("\n" + "=" * 70)
    print("BƯỚC 2: CHẠY KIỂM THỬ CÁC CÂU HỎI QUA QUY TRÌNH DAG VỚI TRỢ LÝ TUYỂN SINH")
    print("=" * 70)

    chat_service = AssistantChatService()
    results = []

    for idx, tc in enumerate(TEST_QUERIES, 1):
        print("\n----------------------------------------------------------------------")
        print(f"[{tc['id']}] {tc['category']}")
        print(f"Câu hỏi: \"{tc['question']}\"")
        print(f"Dự kiến luồng DAG: {tc['expected_branch']}")
        print(f"Tiêu chí chuẩn: {tc['ground_truth_criteria']}")
        print("----------------------------------------------------------------------")

        t0 = time.perf_counter()
        async with AsyncSessionFactory() as session:
            try:
                req = AssistantChatRequest(
                    message=tc["question"],
                    conversation_id=f"test_dag_eval_{tc['id'].lower()}_{int(time.time())}",
                    tenant_id="tenant_qnu",
                )
                resp = await chat_service.chat(
                    db=session,
                    reference="admissions",
                    request=req,
                    correlation_id=f"corr_eval_{tc['id'].lower()}",
                )
                elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

                print(f"[KẾT QUẢ PHẢN HỒI] ({elapsed_ms}ms, status={resp.status}):")
                print(resp.answer.strip())

                citation_count = len(resp.citations) if resp.citations else 0
                print(f"\n[TRÍCH DẪN ({citation_count})]")
                if resp.citations:
                    for c in resp.citations[:3]:
                        if isinstance(c, dict):
                            print(f"  - Document: {c.get('document_id')} | Section: {c.get('section')} | Page: {c.get('page_number')}")
                        else:
                            print(f"  - Document: {getattr(c, 'document_id', '')} | Section: {getattr(c, 'section', '')}")

                results.append({
                    "id": tc["id"],
                    "category": tc["category"],
                    "question": tc["question"],
                    "status": resp.status,
                    "answer": resp.answer,
                    "citations_count": citation_count,
                    "latency_ms": elapsed_ms,
                    "expected_branch": tc["expected_branch"],
                    "ground_truth_criteria": tc["ground_truth_criteria"],
                })

            except Exception as exc:
                elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
                print(f"[!] LỖI THỰC THI: {exc}")
                results.append({
                    "id": tc["id"],
                    "category": tc["category"],
                    "question": tc["question"],
                    "status": "error",
                    "error": str(exc),
                    "latency_ms": elapsed_ms,
                })

    return results


async def main():
    await step_ingest_documents()
    results = await step_test_dag_queries()
    print("\n" + "=" * 70)
    print("TỔNG KẾT KẾT QUẢ KIỂM THỬ:")
    for r in results:
        status_label = "✅ PASS" if r.get("status") in ("answered", "completed") else "❌ FAIL"
        print(f"[{r['id']}] {status_label} ({r.get('latency_ms')}ms) - {r['category']}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
