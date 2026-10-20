# Context564 — Bàn giao

**Trạng thái: PARTIAL — packing đã sửa, Reviewed Fact chat E2E còn blocker độc lập.**

| Điều kiện | Kết quả |
|---|---|
| `_fact_groups` giữ đúng canonical source row | PASS; dùng lại đối tượng đã xác minh, duyệt cả refs của row |
| Header/note/condition bắc cầu, list member/ancestor refs | PASS; không kéo ngược consumer/sibling không liên quan |
| Atomic packing → claim projection | PASS trong 27 tests mới và fixture published integration |
| Missing/duplicate/cross revision/hash guards | PASS các negatives; không bắt exception để bỏ qua |
| Snapshot và cấu hình hiện hành | Hash trước/sau khớp; không reindex/republish/model change |
| Focused | 343 PASS, exit 0 |
| Full backend | **2693 PASS / 18 FAIL / 17 SKIP**, 23 subtests PASS, exit 1 |
| Regression so với562 | 27 added PASS; 0 changed/removed; exact18 failure IDs/causes giữ nguyên |
| Knowledge đoạn văn qua backend TCP thật | **LIVE_E2E_PASS**, 1 citation xác minh identity/hash/quote |
| Social / thanks / follow-up routing | PASS; giữ AM-0007 và năm 2025, không 409 cuối |
| Reviewed Fact AM-0007/SV/2026, follow-up2025 | **FAIL**: insufficient_context, chưa chọn đúng fact |
| Có thể benchmark numeric RAG như đã hoàn thiện? | **Chưa**; phải xử lý entity/metric binding trước |

Blocker thực tế: query analysis chưa nhận mã alphanumeric AM-0007, table decision không gắn thực thể dù lookup có facts. Có thêm rủi ro projection trùng metric giữa cột chỉ tiêu và ghi nhận. Các thành phần này ngoài scope minimal packing fix; không sửa dữ liệu/Intent Router/semantic engine hoặc bật cấu hình khác để báo PASS.

Đọc [Root cause](ROOT_CAUSE_AND_FIX.md), [Closure](DEPENDENCY_CLOSURE_VALIDATION.md), [Implementation](IMPLEMENTATION_REPORT.md), [Tests](TEST_REPORT.md), [Live E2E](LIVE_RAG_E2E_REPORT.md) và [Exact test IDs](REGRESSION_IDS.md).

DB test, 11 hội thoại và 8 gap records kiểm thử đã dọn; usage audit/evidence được giữ. Kiểm duyệt tự động chặn xóa runtime Storage riêng với lý do **blocked by policy**; không tắt bảo vệ hoặc thử cách xóa thay thế.

Agent không stage/commit/push/deploy/restart. Trong phiên có commit ngoài agent `32cdc36b`; đã bảo toàn thay đổi đồng thời.
