# Phiên519 — Kiểm tra 5 câu hỏi tuyển sinh sau khi xuất bản bản Markdown sạch

## Phạm vi

Người dùng yêu cầu tiếp tục kiểm tra 5 câu hỏi tuyển sinh sau phiên518 xuất bản
bản sạch bảng 52 ngành trong app local. Chỉ đo và báo cáo; không sửa
code/dữ liệu/cấu hình, không reset/migration/reindex/publish, không restart,
không commit/push, không bật fallback cloud.

## Thực hiện và bằng chứng

- Ứng dụng bật lại (Docker Desktop); `/health` 200 (database/redis connected).
- Preflight: assistant `ast_admissions`/`col_admissions`, updated_at
  `2026-10-17T09:08:00`, config_sha `4811e541fbdb2d11`; preferred
  `prov_rtx5090_vllm`/`qwen3.5-9b`, `fallback_provider_id=null`; retrieval
  configured 20/20/30/5, `max_context_chars=36000`; reranker bge-reranker-v2-m3.
- Publication: fingerprint `ada86b2e27810441d242`, 22 nguồn, 2772 block (gồm
  `ks_rev_be5b393c11af` của bản sạch 52 ngành đã xuất bản ở518).
- Chạy 5 câu tuần tự trong 1 hội thoại `eval509_1c06c59100a1`, không gửi
  expected_answer.

## Kết quả

| # | Câu hỏi | HTTP | status/decision | cites | Nhãn |
|---|---|---|---|---|---|
| 1 | Tuyển ngành nào năm 2025 | 503 | ALL_PROVIDERS_UNAVAILABLE | 0 | ERROR |
| 2 | Mã ngành Vật lý kỹ thuật | 200 | answered/supported | 1 | PASS |
| 3 | Ngành đó có chuyên ngành gì/đã tuyển? | 200 | insufficient_context/clarify | 0 | FAIL |
| 4 | 2025 có tuyển Trí tuệ nhân tạo? | 200 | answered/supported | 3 | PASS |
| 5 | Danh sách 2025 có áp dụng 2026? | 200 | insufficient_context | 0 | CORRECT_ABSTENTION |

- Tổng hợp chạy chính: PASS2/FAIL1/CORRECT_ABSTENTION1/ERROR1.
- Câu1 retry bổ sung (hội thoại riêng): HTTP200 nhưng
  `VISIBLE_ANSWER_NOT_SUPPORTED`/`ANSWER_SPAN_BUDGET_EXCEEDED`, coverage
  `enumeration`, 0 citation → FAIL. Câu hỏi liệt kê ngành không dựng được đáp án
  có căn cứ từ nguồn sạch vừa xuất bản.
- Câu2 trả `7520401` (Vật lý kỹ thuật - Chuyên ngành Bán dẫn), cite
  `ks_rev_141dd1405ead:8814:9109` trang3; binding gắn `temporal_scope=proposed`.
- Câu3 `conversation-resolution-v1`/`clarify`/`UNRESOLVED_FOLLOWUP`: không nối
  được "ngành đó" về câu2.
- Câu4 trả bảng chỉ tiêu 2025 Trí tuệ nhân tạo (55/50/20) từ nguồn
  `Thông tin TSĐH cập nhật`, 3 citation verify.
- Câu5 `NUMERIC_GROUNDING_FAILED` (số `15`) + `window_repack MODEL_CONTEXT_EXCEEDED`;
  từ chối chốt 2026 là hợp lý nhưng do guard, không phải kết luận "nguồn không nêu".

## Phát hiện phụ

- PG thiếu `unaccent`/`pg_trgm` (chỉ `plpgsql`); truy vấn không dấu đi nhánh ILIKE
  `func.unaccent` → `function unaccent(text) does not exist` → abort transaction →
  503 `EVIDENCE_SOURCE_UNAVAILABLE`. Câu có dấu không đi nhánh này.
- Log có client lặp kết nối `database "qnu" does not exist` (ngoài app).

## Kiểm chứng và giới hạn

- Artifact: `backend/storage/eval509_5q/` (`run.json`, `run.jsonl`,
  `q1..q5_response.json`, `grading_eval509_5q.json`, `results_eval509_5q.csv`,
  `preflight_*.json`, `q1_retry_response.json`, `REPORT_eval509_5q.md`).
- Không sửa production code, không chạy full pytest, không deploy/Git.
- Lượt chạy không phải benchmark; nhãn do người chấm. UI/grading tự động và so
  sánh với bản phục vụ trước đó: NOT RUN.
