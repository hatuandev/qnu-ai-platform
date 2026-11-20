"""Run comprehensive multi-document evaluation suite on the unified 4-document collection."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from qnu.api.wiring import build_container
from qnu.domains.identity.actor import AuthActor
from qnu.domains.rag.answer.schemas import AnswerRequest
from qnu.domains.rag.answer.service import answer
from qnu.platform.config import get_settings
from qnu.platform.database import AsyncSessionFactory

WORKSPACE_ID = "ws_623614ba7fb8"
COLLECTION_ID = "col_unified_212bb3aa"


async def run_single_query(
    c,
    actor,
    workspace_id: str,
    collection_id: str,
    question: str,
    name: str,
    history: list[dict] | None = None,
    conversation_memory: dict | None = None,
):
    print("\n" + "=" * 80)
    print(f"RUNNING EVAL: [{name}]")
    print(f"Question: {question}")
    if history:
        print(f"History: {len(history)} turn(s)")
    t0 = time.perf_counter()
    async with AsyncSessionFactory() as db:
        resp = await answer(
            db,
            c.blob_store,
            c.embedding_model,
            c.vector_store,
            c.chat_model,
            actor,
            workspace_id,
            collection_id,
            AnswerRequest(
                question=question,
                history=history,
                semantic_cache=False,
                conversation_memory=conversation_memory,
            ),
            reranker=c.reranker,
        )
    latency = time.perf_counter() - t0
    trace_dict = resp.trace.model_dump() if resp.trace else {}

    eids = []
    for s in resp.statements or []:
        eids.extend(s.evidence_ids)
    unique_eids = list(dict.fromkeys(eids))

    ans_text = "\n".join(s.text for s in resp.statements or []) + (resp.message or "")
    leak = "<phan_tich>" in ans_text or "</phan_tich>" in ans_text

    # Extract source titles from resp.sources
    source_titles = list(
        {s.source_title for s in (resp.sources or []) if s.source_title}
    )

    print(f"Status: {resp.status} | Latency: {latency:.2f}s | Leak: {leak}")
    print(f"Sources cited: {source_titles}")
    print(f"Evidence IDs: {unique_eids}")
    for idx, s in enumerate(resp.statements or []):
        print(f"  [{idx}] ({s.evidence_ids}): {s.text}")
    if resp.message:
        print(f"Message: {resp.message}")

    return {
        "name": name,
        "question": question,
        "status": resp.status,
        "latency": round(latency, 2),
        "leak": leak,
        "evidence_ids": unique_eids,
        "source_titles": source_titles,
        "statements": [s.text for s in resp.statements or []],
        "message": resp.message,
        "trace": trace_dict,
        "resp_obj": resp,
    }


async def main():
    settings = get_settings()
    c = build_container(settings)
    actor = AuthActor(
        actor_id="act_dev_admin",
        username="dev_admin",
        email="admin@qnu.edu.vn",
        display_name="Dev Admin",
        roles=["admin"],
        authenticated=True,
    )

    print("=" * 80)
    print("BẮT ĐẦU KIỂM THỬ THỰC CHIẾN TRÊN KHO HỢP NHẤT 4 TÀI LIỆU")
    print(f"Collection: {COLLECTION_ID}")
    print("=" * 80)

    results = {}

    # 1. CDS-2 (Tài liệu 1: 4740 - Nhiều ý ghép)
    q_cds2 = "Cơ sở giáo dục đại học phải cập nhật kết quả tự đánh giá lên hệ thống cơ sở dữ liệu ngành Giáo dục trước thời điểm nào hằng năm và đơn vị nào chủ trì đánh giá ngoài?"
    results["CDS-2"] = await run_single_query(
        c, actor, WORKSPACE_ID, COLLECTION_ID, q_cds2, "CDS-2"
    )

    # 2. CDS-3 (Tài liệu 1: 4740 - Hai tiêu chí độc lập)
    q_cds3 = "Tiêu chí triển khai hệ thống LMS/LCMS tối đa bao nhiêu điểm và yêu cầu triển khai thư viện điện tử/thư viện số gồm những nội dung nào?"
    results["CDS-3"] = await run_single_query(
        c, actor, WORKSPACE_ID, COLLECTION_ID, q_cds3, "CDS-3"
    )

    # 3. AUN-2 (Tài liệu 2: KH130 - Nhiều nhiệm vụ ghép)
    q_aun2 = "Nhiệm vụ thẩm định báo cáo tự đánh giá SAR và chuẩn bị hồ sơ minh chứng được giao cho những đơn vị nào, mốc thời gian hoàn thành khi nào?"
    results["AUN-2"] = await run_single_query(
        c, actor, WORKSPACE_ID, COLLECTION_ID, q_aun2, "AUN-2"
    )

    # 4. AUN-3 (Tài liệu 2: KH130 - Hậu cần & đầu mối)
    q_aun3 = "Công tác chuẩn bị hậu cần, cơ sở vật chất và đầu mối liên hệ phục vụ đoàn đánh giá ngoài AUN-QA do các đơn vị nào đảm nhiệm?"
    results["AUN-3"] = await run_single_query(
        c, actor, WORKSPACE_ID, COLLECTION_ID, q_aun3, "AUN-3"
    )

    # 5. KH07-1 (Tài liệu 3: KH 07/KH-AM - Bảng tài chính / phân bổ năm)
    q_kh07_1 = "Tổng kinh phí dự kiến cho đề án theo Kế hoạch 07/KH-AM là bao nhiêu và được phân bổ qua các năm 2025, 2026, 2027, 2028 như thế nào?"
    results["KH07-1"] = await run_single_query(
        c, actor, WORKSPACE_ID, COLLECTION_ID, q_kh07_1, "KH07-1"
    )

    # 6. KH07-2 (Tài liệu 3: KH 07/KH-AM - Chủ trì & phối hợp)
    q_kh07_2 = (
        "Nhiệm vụ phát triển hạ tầng AI Lab theo Kế hoạch 07/KH-AM do đơn vị nào chủ trì và phối hợp?"
    )
    results["KH07-2"] = await run_single_query(
        c, actor, WORKSPACE_ID, COLLECTION_ID, q_kh07_2, "KH07-2"
    )

    # 7. TS-1 (Tài liệu 4: Tuyển sinh 2026 - Bảng số liệu & tổ hợp môn)
    q_ts1 = "Chỉ tiêu và điểm chuẩn trúng tuyển ngành Sư phạm Lịch sử - Địa lý (mã ngành 7140249) năm 2024 và năm 2025 là bao nhiêu?"
    results["TS-1"] = await run_single_query(c, actor, WORKSPACE_ID, COLLECTION_ID, q_ts1, "TS-1")

    # 8. TS-2 (Tài liệu 4: Tuyển sinh 2026 - Quy chế ngoại lệ thể hình)
    q_ts2 = "Thí sinh nam có chiều cao 1m62 có đủ điều kiện đăng ký xét tuyển ngành Giáo dục Thể chất không? Vì sao?"
    results["TS-2"] = await run_single_query(c, actor, WORKSPACE_ID, COLLECTION_ID, q_ts2, "TS-2")

    # 9. CROSS-1 (So sánh liên văn bản: Phân định vai trò Phòng Đào tạo giữa KH 130 và KH 07)
    q_cross1 = "So sánh vai trò và nhiệm vụ của Phòng Đào tạo giữa Kế hoạch số 130/KH-ĐHQN và Kế hoạch số 07/KH-AM."
    results["CROSS-1"] = await run_single_query(
        c, actor, WORKSPACE_ID, COLLECTION_ID, q_cross1, "CROSS-1"
    )

    # 10. MULTI-T1 & MULTI-T2 (Hội thoại đa lượt có nhớ mạch an toàn)
    q_multi_t1 = "Trong Kế hoạch số 130/KH-ĐHQN, Nhiệm vụ 1 về hoàn thiện báo cáo SAR có thời gian thực hiện khi nào?"
    r_multi_t1 = await run_single_query(
        c, actor, WORKSPACE_ID, COLLECTION_ID, q_multi_t1, "MULTI-T1"
    )
    results["MULTI-T1"] = r_multi_t1

    # Tạo TurnHistory từ T1
    t1_answer_text = (
        "\n".join(r_multi_t1["statements"])
        if r_multi_t1["statements"]
        else (r_multi_t1["message"] or "")
    )
    history = [{"question": q_multi_t1, "answer": t1_answer_text}]
    conv_mem = {
        "active_document": "Kế hoạch 130/KH-ĐHQN",
        "last_entity": "Nhiệm vụ 1",
        "prior_entity": None,
        "grounded_conclusions": [
            {
                "question": q_multi_t1,
                "conclusion": "Tháng 01/2026",
            }
        ],
        "summary_text": "Văn bản đang trao đổi: Kế hoạch 130/KH-ĐHQN. Mục vừa đối chiếu: Nhiệm vụ 1",
    }

    # Turn 2: Hỏi thuộc tính mới cùng thực thể không lặp lại tên
    q_multi_t2 = "Đơn vị nào chủ trì và phối hợp?"
    results["MULTI-T2"] = await run_single_query(
        c,
        actor,
        WORKSPACE_ID,
        COLLECTION_ID,
        q_multi_t2,
        "MULTI-T2",
        history=history,
        conversation_memory=conv_mem,
    )

    # 11. OOS-1 (Ngoài phạm vi tài liệu -> Chống suy đoán / Insufficient Evidence)
    q_oos1 = "Quy định về định mức giờ chuẩn giảng dạy và chế độ nghỉ hè của giảng viên năm 2026 theo Nghị định 97/2023 là gì?"
    results["OOS-1"] = await run_single_query(
        c, actor, WORKSPACE_ID, COLLECTION_ID, q_oos1, "OOS-1"
    )

    # Serialize results to file
    out_file = Path("unified_4docs_eval_results.json")
    clean_results = {}
    for k, v in results.items():
        copy_v = dict(v)
        copy_v.pop("resp_obj", None)
        clean_results[k] = copy_v

    with open(out_file, "w", encoding="utf-8") as f:  # noqa: ASYNC230
        json.dump(clean_results, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 80)
    print(f"ĐÃ HOÀN THÀNH TOÀN BỘ KIỂM THỬ VÀ LƯU KẾT QUẢ TẠI: {out_file}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
