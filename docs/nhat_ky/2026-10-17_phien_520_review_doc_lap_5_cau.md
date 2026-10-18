# Phiên520 — Review độc lập kết quả5câu sau xuất bản

## Phạm vi

User yêu cầu xem lượt test đã chạy. Chỉ đọc artifact519, mã hiện tại và truy vấn
DB kiểm citations/extensions; không chạy lại model hoặc sửa code/config/dữ liệu.
Skill qnu-rag-evaluation yêu cầu chấm đúng câu hỏi, không đồng nhất fail-closed
với từ chối đúng. Giữ nguyên nhãn/báo cáo gốc519 để truy vết.

## Đánh giá lại theo tiêu chí dùng thực tế

| Câu | Nhãn review | Bằng chứng |
| --- | --- | --- |
| 1 | ERROR | Main run HTTP503 ALL_PROVIDERS_UNAVAILABLE; không phải thiếu nguồn. |
| 2 | PASS | Mã đúng câu hỏi hẹp, quote/hash/span canonical xác minh lại khớp; còn STT thừa trong đáp án. |
| 3 | FAIL | UNRESOLVED_FOLLOWUP, hỏi lại chủ đề dù câu2 đã nêu rõ ngành. |
| 4 | PARTIAL | Facts/citations có căn cứ nhưng không trả lời trực tiếp có/không, thừa bảng chỉ tiêu/điểm và ghi chú dang dở. |
| 5 | FAIL | Hỏi phạm vi áp dụng giữa2025/2026 nhưng nhận câu không chốt được con số; không chứng minh correct abstention. |

Theo rubric đầu ra đầy đủ/trọng tâm/trình bày đã giao: **1PASS/1PARTIAL/2FAIL/
1ERROR** trên5câu. Đây là nhãn review độc lập, không sửa kết quả gốc hoặc suy
độ chính xác toàn chatbot. Câu4 có thể coi đạt riêng correctness của số liệu;
PARTIAL ở đây là chất lượng trả lời yêu cầu thực tế, không kết luận facts sai.

Retry riêng câu1 không tính vào5lượt chính: HTTP200 nhưng insufficient_context,
VISIBLE_ANSWER_NOT_SUPPORTED/ANSWER_SPAN_BUDGET_EXCEEDED; là FAIL hành vi bổ sung,
không thay thế ERROR chính để làm đẹp tỉ lệ.

## Truy vết nguyên nhân và giới hạn

- Câu1 retry đi fact_hybrid, packing2186chars dưới max36000, nhưng visible audit
  từ chối ANSWER_SPAN_BUDGET_EXCEEDED. `response_audit.py` chặn khi rỗng, quá24
  spans hoặc một span quá4000chars; artifact không giữ draft nên chưa xác định
  chắc điều kiện nào. Không gọi lỗi này là hết ngân sách context hoặc sửa bằng
  tăng TopK. Fallback coverage enumeration vẫn không có danh sách được xác minh.
- Câu3: resolver chỉ nhận các câu user trước làm antecedents; UNRESOLVED_FOLLOWUP
  dùng chung cho nhiều điều kiện sai. Log chưa có raw resolution/guard reason
  riêng nên chưa khẳng định model chọn sai ID, rewrite hay guard số đã chặn.
  Hành vi không nối được câu2→câu3 là quan sát thật.
- Câu4: raw answer gồm bảng số liệu và câu dẫn ghi chú kết thúc bằng dấu hai chấm,
  không có phần ghi chú sau đó. Không chỉ lấy status=supported để chấm UX PASS.
- Câu5: NUMERIC_GROUNDING_FAILED (số15); prose fallback gặp MODEL_CONTEXT_EXCEEDED,
  repack7blocks/9418chars xuống1block/2315chars rồi NO_UNAMBIGUOUS_BOUND_PROSE.
  Cơ chế từ chối tránh bịa, nhưng câu trả lời không giải quyết chuyển năm. Không
  suy rằng tài liệu2026 thiếu chỉ từ việc guard từ chối bản nháp.
- Hai câu có đáp án/citations (2và4) đều trích nguồn khác, không phải bản PDF sạch
  vừa xuất bản. Chưa có answer baseline trước sửa; không có bằng chứng cải thiện
  RAG do thao tác làm sạch nguồn. Không tăng test số lượng để thay phân tích.
- `served_models` trong các file tích lũy cùng prefix qua các lượt (1/7/8/11/14
  records); không dùng nó làm số lần gọi riêng từng câu nếu chưa lọc correlation.

## Kiểm chứng đọc DB hiện tại

- Query pg_available_extensions: unaccent và pg_trgm có sẵn nhưng installed_version
  đều null. Code `retriever.py` nhánh không dấu gọi func.unaccent; báo cáo519 ghi
  lỗi function missing làm abort transaction. Không có callpg_trgm trong nhánh
  đã xem, nên không gộp cả hai extension thành nguyên nhân trực tiếp của503.
- Source/hash/span của toàn bộ4citations câu2/câu4 đều khớp canonical hiện tại
  và quote là đúng substring. Điều này chứng minh citation binding, không thay
  kiểm định PDF gốc hoặc biến temporal proposed thành verified.

## Đề xuất

1. Chặn lỗi phụ thuộc DB không dấu theo migration/capability thích hợp và giữ
   transaction an toàn; tách ERROR provider khỏi no-answer. Không tự apply DB.
2. Ưu tiên luồng liệt kê bảng đầy đủ và budget audit phù hợp danh sách dài,
   giữ nguồn/năm/định danh; không tăng đồng loạt TopK hoặc bỏ verifier.
3. Sửa follow-up và trả lời theo intent: nối thực thể câu trước, xử lý đổi năm,
   không tự kéo số liệu ngoài yêu cầu; packing tính cả prompt/output/window.

Sau khi được giao sửa, test lại đúng các ca lỗi; chưa cần82câu hoặc reset nguồn.

## Lệnh và trạng thái

- PowerShell Get-Content/rg đọc report519 và các q1..q5_response.json, retry,
  grading/preflight, runtime code; không sửa raw artifacts.
- CWDbackend `.venv/Scripts/python.exe -`: SELECT extensions và kiểm canonical
  quote/hash/span của câu2/4, exit0/PASS. Không gọi model hoặc ghi DB.
- Không productioncode/fullpytest/build/UI, không inference benchmark,
  migration/restart/publish/Git. Tài liệu review là thay đổi duy nhất của phiên.
