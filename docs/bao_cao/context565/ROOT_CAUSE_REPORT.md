# Context565 — Nguyên nhân và phạm vi sửa

Ngày 2026-10-20. Triển khai prompt Context565 cùng 5 bổ sung đã duyệt. Không thay nguồn, revision, index, publication hoặc ModelOps settings.

## Các lỗi độc lập

1. `query_router.py` chỉ nhận mã ngành 7 chữ số; ánh xạ tên ngành có thể thêm một mã ngành khác dù câu hỏi đã có mã rõ ràng. Mã chữ-số/zero đầu cần giữ nguyên và phải đối chiếu nguồn, không coi regex là xác minh.
2. `table_context.row_identities` nhận cột mã bằng mẫu thiên về số, đồng thời cột mã chữ-số bị đưa vào danh sách tên. Với nguồn thật, DB có facts nhưng `entity_code` để null. Thay regex query một mình không sửa được metadata đã xuất bản.
3. Catalog cũ gộp `Số lượng`, `SL` vào quota. Header nhiều tầng `Ghi nhận / Số lượng` vì vậy có thể trở thành `expected_quota`. Predicate attribute cũ còn có thể loại mất candidate trước khi giải nghĩa từ nguồn.
4. `FactLayer.lookup_facts` áp identity trước LIMIT chủ yếu cho mã số; các OR keyword/value không đủ chứng minh thực thể. `temporal_answer` lại chỉ chấp nhận mã 7 số và chưa tách đơn vị/đại lượng đầy đủ.
5. Live test phát hiện lỗi tích hợp: người dùng đổi sang số ghi nhận nhưng rewrite vẫn giữ chữ chỉ tiêu. Phân tích toàn chuỗi rewrite + current turn bằng ưu tiên keyword đã chọn nhầm cột. Đây là ca **HTTP 200, citation hợp lệ nhưng số liệu trả lời sai metric**; batch bị dừng tại L04 và được giữ làm bằng chứng RED.

## Thay đổi

Hai helper thuần dùng chung cho code candidates và metric roles, không có prefix/tên tài liệu/gold thử nghiệm trong ứng dụng. Row identity ưu tiên cột code/name từ header; dấu phân cách và zero đầu được bảo toàn. Bare quantity giữ raw content/unknown, không biến thành quota.

Resolver đọc snapshot đã pin, xác minh canonical blocks/hash/manifest, table header và raw row. Nó đối chiếu facts với đúng artifact/row/column/value, rồi chỉ tạo view trong bộ nhớ cho nhãn dẫn xuất chưa có human override. Tọa độ dòng và cột metric đúng được lọc trong SQL trước LIMIT. Không rebuild hoặc ghi lại artifact cũ.

Service giữ metric/đơn vị được nói rõ ở current turn trong private request context; phần được kế thừa chỉ bổ sung identity/năm. Đây là kiểm tra constraint tại Fact Resolution, không thay Intent Router, Memory hay model prompt. Không thêm lượt LLM cho numeric selection.

Selected materialized facts đi qua `reviewed_fact_blocks`, atomic pack và `source_grounded_claims` trước trả lời. Citation trỏ raw canonical row; chú thích bắt buộc được giữ nguyên phạm vi và trích nguyên văn khi có. Budget không đổi.

## Bằng chứng

- RED ban đầu: 20 FAIL / 5 PASS. Baseline focused trước sửa: 59 PASS.
- RED live: L01/L03 đúng nhưng L04 chọn quota thay vì recorded count; không gọi batch đó PASS.
- Sau sửa: batch ứng dụng thật 13/13 cases đạt; TCP backend đang chạy 8/8 cases đạt. Giá trị và tọa độ kiểm lại từ nguồn độc lập, xem [LIVE_RAG_E2E_REPORT](LIVE_RAG_E2E_REPORT.md).
- Unit/integration cuối: 253 PASS,54testinstances mới. Full gate và exact IDs tại [VALIDATION_REPORT](VALIDATION_REPORT.md).

Không cần đổi Qwen/context/top-K, không tự approve unknown. Mã thiếu chứng cứ, metric không rõ, sai đơn vị/năm hoặc thiếu toàn nhóm bằng chứng vẫn chặn.

