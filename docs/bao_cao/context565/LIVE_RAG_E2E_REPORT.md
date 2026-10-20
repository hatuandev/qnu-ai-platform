# Context565 — Kiểm chứng chatbot thực tế

Ngày 2026-10-20. **Numeric Knowledge E2E đã đạt trên snapshot hiện hành.** Batch ASGI có upstream thật: 13/13 cases; backend TCP đang chạy: 8/8 cases. Full regression là gate riêng ở [VALIDATION_REPORT](VALIDATION_REPORT.md), không suy toàn suite PASS từ các ca này.

## Nguồn và gold

Collection `col_admissions`, binding `bnd_fa71a57c9cf1`, source `ks_rev_ca1e7f16d9e0`, index `idx_rev_967891af9d5d` được xác minh lại trước gọi. Không publish/reindex/rebuild/restart. Các ID chỉ ở evidence/report, không được hardcode vào ứng dụng.

Gold lấy trực tiếp từ canonical table đã kiểm hash: code column được xác nhận, đúng row/code, column ID, header path và `field_state=present`. Không lấy số fixture trong prompt hoặc output model làm gold. Source hiện hành có quota2025 thực; không dùng fixture T4 (chỉ có recorded2025) để kết luận sai về tài liệu này.

Values/rows/columns được lưu private tại `backend/storage/context565/live-final/gold-private.json`. Lượt audit tách riêng đọc selected fact IDs từ DB, đối chiếu source unit/column/value với gold và kiểm từng citation bằng exact canonical substring tại span start/end. 23 response qua audit này đạt; không lấy chính resolver đang test làm expected.

## Batch ASGI cuối: app và upstream thật

Auth dùng development actor hiện hành, không override dependency. Spies chỉ đếm rồi gọi nguyên hàm gốc; không thay response của DB/LLM/Qdrant/reranker. Đây là **LOCAL_INTEGRATION_PASS với upstream thật**; transport TCP xác nhận LIVE_E2E bên dưới.

| ID | Câu hỏi/chuỗi | Thực tế | Citation | ms | Kết quả |
|---|---|---|---:|---:|---|
| L01 | Chỉ tiêu (SV), mã AM-0007, năm2026 | Đúng quota/cell; materialized fact → closure/projection PASS | 1 | 876,15 | PASS |
| L02 | Cảm ơn, cùng conversation | SOCIAL, không retrieval/model | 0 | 204,88 | PASS |
| L03 | Còn năm2025? | Giữ entity/quota, đổi đúng năm; closure/projection PASS | 2 | 2429,60 | PASS |
| L04 | Còn số lượng ghi nhận (SV) năm2025? | Current metric thắng quota cũ; đúng recorded column; closure/projection PASS | 2 | 2540,09 | PASS |
| L05 | Số ghi nhận (SV), AM-0007, năm2026 | Đúng recorded count, không lấy quota; closure/projection PASS | 1 | 819,81 | PASS |
| L06 | Chỉ tiêu (SV), AM-0070, năm2026 | Đúng entity/row khác, không lấy AM-0007; closure/projection PASS | 1 | 624,08 | PASS |
| L07 | Chỉ tiêu AM-0007, năm2098 | insufficient_context; không lấy năm khác | 0 | 642,18 | PASS negative |
| L08 | Chỉ tiêu AM-0099, năm2026 | Mã chưa được nguồn chứng minh; không fallback sang mã gần | 0 | 546,84 | PASS negative |
| L09 | Số lượng AM-0007 năm2026, chưa rõ loại đại lượng | METRIC_UNVERIFIED; không tự chọn quota/recorded | 0 | 534,27 | PASS negative |
| L10 | Chỉ tiêu **lớp** AM-0007 năm2026 | Không dùng ô đơn vị SV | 0 | 818,43 | PASS negative |
| L11 | Chỉ tiêu AM-0007, không nêu năm | DATA_YEAR_REQUIRED | 0 | 602,13 | PASS negative |
| L12 | Xin chào | SOCIAL, không retrieval/model | 0 | 216,96 | PASS |
| L13 | Tài liệu mô phỏng có giá trị áp dụng thực tế không? | Answered, canonical prose verification/citation hợp lệ | 1 | 11841,23 | PASS prose |

Mọi case HTTP200. Positive numeric PASS yêu cầu code, metric, year, literal value, unit, source row/column, hash/revision và citation đều đúng; không coi HTTP200 hoặc no409 là đủ. Negative refusal không thay cho positive numeric PASS.

### Stage đã thực thi

- L01/L05/L06: Fact Layer1, table selection có matched fact, packing/closure/projection PASS. **0 Qdrant, 0 reranker, 0 LLM**; đây là deterministic structured fact answer, không tuyên bố dense retrieval.
- L03/L04: mỗi ca có một Qwen call để resolve follow-up và một Fact Layer call; numeric answer vẫn từ ô đã xác minh.
- L02/L12: không model/retrieval.
- L13: retrieve1, sparse theo retriever hiện hành, dense1, embedding1, Qdrant query1, reranker2, Qwen generate5. Final answer qua verified canonical prose fallback sau retrieval; không quy toàn đáp án cho dense hit.

Qwen3.5-9b/provider hiện hành được giữ. Không đổi context window, evidence-policy enabled flag hoặc prompt model. Có source note thì trích raw context với phạm vi gốc; không tự mở rộng ý nghĩa sang mọi năm/nhóm.

## TCP backend đang chạy

Gọi HTTP thật tới local backend đang hoạt động, `/health/live`200; không restart. Một conversation thực gồm8requests, sau đó dọn. 5 numeric responses đều có selected fact và closure/projection PASS, citation exact source span; 2 social responses và1negative đúng.

| ID | Case | Status | ms | Kết quả |
|---|---|---|---:|---|
| TCP01 | Quota AM-0007/2026 | answered | 903,08 | LIVE_E2E_PASS |
| TCP02 | Cảm ơn | answered | 189,11 | PASS social |
| TCP03 | Năm2025 | answered, đúng quota2025 | 2259,30 | LIVE_E2E_PASS |
| TCP04 | Đổi sang recorded2025 | answered, đúng metric/cột | 2136,96 | LIVE_E2E_PASS |
| TCP05 | Recorded AM-0007/2026 | answered | 445,30 | LIVE_E2E_PASS |
| TCP06 | Quota AM-0070/2026 | answered, đúng row khác | 443,80 | LIVE_E2E_PASS |
| TCP07 | Năm2098 | insufficient_context | 647,01 | PASS negative |
| TCP08 | Xin chào | answered | 195,63 | PASS social |

Usage audit TCP: **2 Qwen3.5-9b success**, dùng cho hai follow-ups; không fallback. Không thể gán stage counts từ TCP riêng; forward-only ASGI trace cung cấp bằng chứng stage. Không browser automation trong task; không gọi đây là UI E2E hoặc đo SLA/load.

Sau rà soát multi-entity/unit/debug và source-row fallback, chạy thêm2TCPrequests độc lập trên mã cuối: quota AM-0007/2026 (public,954,82ms) và recorded AM-0007/2026 (debug,524,87ms), cả2đúng source/citation. Public không có fact_resolution trace; debug có trace và proof PASS. Usage0modelcalls; receipts `tcp-final-*.json`. Không gọi lại các ca LLM đã đạt.

## RED live và cleanup

Batch đầu dừng tại L04: rewrite bỏ thay đổi metric nên chọn quota2025 dù người dùng hỏi recorded2025. Receipt FAIL được giữ, sau đó sửa current metric constraint và chạy batch cuối mới. Không resend uncertain attempt; batch trước đã kết thúc/cleanup trước khi tạo lượt mới.

Tổng14ownconversations được dọn (1 RED +10 finalASGI +1 TCP +2 scalar TCP cuối), 6 gap records mới dọn; usage audit giữ nguyên. DB test và runtime cleanup có kết quả cuối trong VALIDATION_REPORT. Evidence private không đưa corpus hoặc credentials vào Git.

Public source/index/config seals trước/sau khớp. Không thay semantic approval; “published materialized fact proof” không đồng nghĩa mọi semantic proposal đã được người dùng duyệt. Benchmark85% và production readiness **NOT RUN**.
