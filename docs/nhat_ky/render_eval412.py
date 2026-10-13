"""Render recorded live test evidence into a reviewable Markdown report."""

import json
import statistics
import sys
from collections import Counter
from pathlib import Path


def main() -> None:
    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    lines = [
        "# Kết quả kiểm thử bộ câu hỏi tuyển sinh 2026",
        "",
        "Kết luận: chatbot hiện chưa đạt yêu cầu tư vấn thực tế với bộ câu hỏi này.",
        "",
        "## Phạm vi và phương pháp",
        "",
        f"- Trích xuất {len(payload['cases'])} cặp Hỏi–Đáp, 16 nhóm, từ DOCX người dùng cung cấp.",
        f"- Bắt đầu UTC: {payload['started_at']}; hoàn tất UTC: {payload.get('finished_at', 'đang chạy')}.",
        f"- SHA-256 DOCX: `{payload['document_sha256']}`.",
        (
            f"- Kho: `{payload['publication']['collection_id']}`, epoch {payload['publication']['epoch']}, "
            f"generation `{payload['publication']['metadata'].get('active_vector_generation_id')}`."
        ),
        "- Gửi nguyên câu hỏi; không đưa đáp án, hướng dẫn trong DOCX hoặc nội dung FAQ vào prompt.",
        (
            "- Mỗi câu dùng một hội thoại mới. Luồng chatbot là DAG thực tế `/assistants/admissions/chat`; "
            "RAG riêng là `/rag/ask` với model/reranker lấy từ cấu hình hiện tại."
        ),
        "- Hai đường có system prompt/runtime policy khác nhau: đây là đối chiếu chẩn đoán, không phải A/B cùng cấu hình.",
        "- Không xóa cache, reset DB, đổi model, upload FAQ, duyệt, nạp lại vector, xuất bản hoặc sửa runtime.",
        "- Có phát sinh các bản ghi hội thoại, workflow, sử dụng model và cache bình thường của việc test.",
        (
            "- Số lượt có trạng thái `answered` chỉ phản ánh hệ thống trả lời, KHÔNG phải số câu đúng. "
            "Không chạy Ragas và không tuyên bố các chỉ số faithfulness/relevance/precision."
        ),
        (
            "- Đáp án trong DOCX là đáp án tham khảo để đối chiếu, không tự động được coi là nguồn pháp lý đã xác thực. "
            "Một số câu không nêu năm; việc chọn tài liệu cũ mà không hỏi rõ/nêu thời gian là rủi ro khi tư vấn mùa 2026."
        ),
        "",
        "## Model thực tế và đối soát trạng thái",
        "",
        (
            "OpenAI và Gemini đang inactive, dù cấu hình trợ lý ghi primary gpt-4o-mini và fallback gemini-2.5-flash-lite. "
            "Nhật ký inference cho các conversation của lần chạy đầy đủ ghi 69 lượt Cloudflare "
            "@cf/meta/llama-3.1-8b-instruct, is_fallback=true, success. "
            "82 bản ghi qnu_workflow mang tên gpt-4o-mini là log tổng hợp theo cấu hình, "
            "không chứng minh đã gọi GPT; service còn ước lượng token từ chiều dài câu hỏi/đáp. "
            "Chưa thử đổi model nên chưa thể quy toàn bộ lỗi chất lượng cho riêng model dự phòng."
        ),
        "",
        (
            "Đối soát sau test: epoch vẫn 3, generation vẫn vg_21324678abcf, "
            "19 bộ binding/source/index pointers không đổi. Đây là lần chạy thực tế với cache hiện có, không cold-cache benchmark."
        ),
        "",
        "## Tổng hợp vận hành",
        "",
        "| Đường kiểm thử | Tổng lượt | HTTP 200 | answered | insufficient_context | Lỗi khác | Trung vị giây |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for route in ("dag", "rag"):
        records = [r for r in payload["results"] if r["route"] == route]
        statuses = Counter(r.get("response", {}).get("status") for r in records)
        successful_http = sum(r.get("http") == 200 and not r.get("exception") for r in records)
        known = statuses["answered"] + statuses["insufficient_context"]
        lines.append(
            f"| {route.upper()} | {len(records)} | {successful_http} | {statuses['answered']} | "
            f"{statuses['insufficient_context']} | {len(records) - known} | "
            f"{statistics.median(r['wall_seconds'] for r in records):.2f} |"
        )
    lines.extend(
        [
            "",
            "## Các lỗi đã xác minh",
            "",
            (
                "1. Câu 1 mã trường: node RAG trả DQN, node citation guard chặn vì `citations list is empty`; "
                "trả thiếu dữ liệu dù đáp án đã được sinh. Không nên tắt guard; cần gắn evidence cho câu trả lời hợp lệ."
            ),
            (
                "2. Câu 5 tổng chỉ tiêu: tài liệu active `Thông tin TSĐH cập nhật` ghi `Tổng số lượng tuyển sinh: 5.173 (chỉ tiêu)`. "
                "RAG trả `NO_COMPATIBLE_FACT_EVIDENCE`: gate chỉ dùng bằng chứng facts/bảng và kết thúc trước hybrid retrieval; "
                "số liệu ở văn bản thường không đi qua được nhánh này."
            ),
            (
                "3. Câu 21 ngành sư phạm có xét học bạ: DAG trả có; câu 36 gần tương đương lại trả không. "
                "Câu trả lời không ổn định theo cách diễn đạt và không đáp ứng đáp án tham khảo 2026."
            ),
            (
                "4. Câu 25 đã nêu rõ năm 2026 nhưng DAG khẳng định môn Tiếng Anh nhân hệ số 2 chỉ từ danh sách tổ hợp. "
                "Trích dẫn không chứng minh hệ số; guard vẫn đánh grounded. Đây là lỗi suy luận bằng chứng, không chỉ lỗi chọn năm."
            ),
            (
                "5. Câu 4 website: DAG trả miền cũ `quynhon.edu.vn`/`tuyensinh.quynhon.edu.vn`, "
                "trong khi nguồn cập nhật có `qnu.edu.vn`/`tuyensinh.qnu.edu.vn`; direct RAG trả miền trong đáp án."
            ),
            (
                "6. Câu 14–15 phương thức GDMN/GDTC: trộn phương thức/chỉ tiêu cũ; câu 15 lấy thông tin năm 2025. "
                "Không thể dùng câu trả lời đó mặc định cho mùa 2026."
            ),
            (
                "7. Kho chưa đủ tài liệu đợt bổ sung cuối mùa, nhưng bot không từ chối an toàn trong các câu tương ứng. "
                "Không tìm thấy số `151/TB-HĐTS`, `158/TB-HĐTS`, `456 chỉ tiêu` trong 19 canonical sources active; "
                "đây không tự nó chứng minh dữ liệu không có, nhưng các thông báo chuyên đề này không có trong danh mục nguồn hiện tại. "
                "Câu 76 nhầm lịch nhập học 24–28/8 thành hạn xét bổ sung; câu 77 dùng tối đa 15 nguyện vọng đợt chính "
                "thay vì 3 theo FAQ; câu 78 dùng 300.000 đồng/thí sinh của thi năng khiếu thay vì 15.000 đồng/nguyện vọng theo FAQ."
            ),
            (
                "8. Tin nhắn no-answer dùng hotline cũ trong cấu hình (`0256.3846.156`), "
                "khác số `1800.55.88.49` ở nguồn tuyển sinh cập nhật và đáp án câu 3."
            ),
            (
                "9. Câu 39 trả GDMN không thi năng khiếu, câu 41 trả GDTC không yêu cầu thể hình; "
                "nguồn 2026 active có đoạn thi GDMN/GDTC và yêu cầu nam 1,65m/45kg, nữ 1,55m/40kg. Guard vẫn cho qua cả hai."
            ),
            (
                "10. Câu 42 hỏi điểm sàn GDMN năm 2026 nhưng DAG trả 20.25. Nguồn điểm sàn active có 20 và điều kiện 13,34; "
                "20.25 lại xuất hiện ở cột điểm trúng tuyển 2023 trong nguồn lịch sử. "
                "Lỗi nhầm loại điểm/năm cho thấy chỉ kiểm tra số có mặt trong context là chưa đủ."
            ),
            "",
            "## Hướng xử lý đề xuất chưa triển khai",
            "",
            (
                "- Ưu tiên nguồn theo thời gian/hiệu lực và phạm vi; thiếu năm thì hỏi làm rõ hoặc nêu rõ năm sử dụng, "
                "không trộn số liệu 2024/2025/2026."
            ),
            (
                "- Mở bằng chứng số liệu cho đoạn văn đã xuất bản: kiểm chứng tuple "
                "(đối tượng, thuộc tính, giá trị, năm, điều kiện, nguồn/trang) trước khi trả; không bỏ gate an toàn."
            ),
            "- Đồng bộ trích dẫn RAG → DAG, kiểm chứng quan hệ/điều kiện/phủ định chứ không chỉ độ trùng từ/số.",
            (
                "- Chọn lại chat model/provider đang hoạt động đúng chủ đích trong ModelOps; "
                "hiển thị model thực sự phục vụ và phân tách log workflow khỏi inference/chi phí để tránh hiểu nhầm đã gọi GPT."
            ),
            (
                "- Phân biệt loại sự kiện và đơn vị: đăng ký nguyện vọng, nộp phí, thi năng khiếu, "
                "xác nhận trên Hệ thống Bộ, nhập học tại trường, xét bổ sung. Không chuyển số giữa các nghiệp vụ."
            ),
            (
                "- Bổ sung nguồn chính thức về kết quả, đợt bổ sung và chính sách hỗ trợ còn thiếu; "
                "FAQ có thể được duyệt thành nguồn riêng nhưng không lấy làm bằng chứng cho chính bài test đang dùng."
            ),
            (
                "- Đưa 82 câu này cùng các biến thể tương đương thành regression evaluation, "
                "đánh giá câu trả lời có căn cứ và từ chối đúng riêng biệt."
            ),
            "",
            "## Ma trận trạng thái từng câu",
            "",
            "| Câu | Câu hỏi | DAG | RAG |",
            "| ---: | --- | --- | --- |",
        ]
    )
    keyed = {(r["id"], r["route"]): r for r in payload["results"]}
    for case in payload["cases"]:
        statuses = [
            keyed.get((case["id"], route), {}).get("response", {}).get("status", "không có")
            for route in ("dag", "rag")
        ]
        lines.append(
            f"| {case['id']} | {case['question'].replace('|', '/')} | {' | '.join(statuses)} |"
        )
    lines.extend(["", "## Nguồn đang phục vụ", ""])
    for source in payload["publication"]["sources"]:
        lines.append(
            f"- {source['title']} — binding `{source['binding_id']}`, index `{source['index_revision_id']}`."
        )
    lines.extend(["", "## Đối chiếu đầy đủ từng câu", ""])
    for case in payload["cases"]:
        lines.extend(
            [
                f"### Câu {case['id']} {case['question']}",
                "",
                f"Nhóm: {case['section']}",
                "",
                "Đáp án tham khảo trong DOCX:",
                "",
                case["expected_answer"],
                "",
            ]
        )
        for route in ("dag", "rag"):
            record = keyed.get((case["id"], route), {})
            response = record.get("response", {})
            lines.extend(
                [
                    (
                        f"{route.upper()} — HTTP {record.get('http')}, trạng thái {response.get('status')}, "
                        f"{record.get('wall_seconds')} giây:"
                    ),
                    "",
                    response.get("answer", str(record.get("exception", "không có"))),
                    "",
                ]
            )
            for citation in response.get("citations", []):
                lines.append(
                    f"- Nguồn: {citation.get('title')} — trang {citation.get('page_number')}; "
                    f"binding `{citation.get('binding_id')}`, index `{citation.get('index_revision_id')}`."
                )
            for node in record.get("trace", []):
                if node["node_type"] == "guard.citation_policy":
                    output = node.get("output", {})
                    lines.extend(
                        [
                            "",
                            "Kiểm tra DAG: "
                            + json.dumps(
                                {
                                    key: output.get(key)
                                    for key in (
                                        "is_grounded",
                                        "failure_reasons",
                                        "unsupported_numbers",
                                    )
                                },
                                ensure_ascii=False,
                            ),
                            "",
                        ]
                    )
            if response.get("execution_id"):
                lines.extend([f"Mã workflow: `{response['execution_id']}`.", ""])
    Path(sys.argv[2]).write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
