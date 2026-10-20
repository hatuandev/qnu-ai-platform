# Phiên 564 — Evidence dependency closure và RAG thực tế

Ngày 2026-10-20. Người dùng cho triển khai prompt Context564 cùng 5 bổ sung: closure có hướng/bắc cầu, budget hiện hành, gold từ nguồn với đúng mã/metric/năm, chứng minh stage thật và negatives/cleanup cô lập. Dùng skills RAG pipeline, clean code và backend hiện có.

## Kết quả và phạm vi

**PARTIAL**. Đã sửa mất canonical source row trong `_fact_groups`; duyệt refs của row và giữ đối tượng đã xác minh. Khi thử API thật, tìm thêm pack list member/ancestor bị mất footnote; đã có red test rồi sửa complete required closure trước tính budget. Không mở ngược shared note sang consumer hoặc enumeration siblings ngoài yêu cầu.

Hai file ứng dụng thay đổi: `backend/app/modules/rag/evidence_dependencies.py`, `backend/app/modules/rag/evidence_blocks.py`. Thêm `backend/tests/test_evidence_closure_564.py` với 27 test instances. Không thay API/schema/Intent Router/memory/parser/semantic annotation/model settings/top-K/context budget/publication.

Tái hiện old-code red: 5 FAIL / 14 PASS, exit 1. Các lỗi directed canonical/member closure cũng có receipts red. Focused cuối 343 PASS, exit 0; full cuối 2693 PASS / 18 FAIL / 17 SKIP + 23 subtests PASS, exit 1. So JUnit với562: 27 added PASS, 0 changed/removed, exact18 failure IDs/causes giống nhau. Full suite vẫn FAIL. Ruff 3 files và diff whitespace PASS; FE NOT RUN vì không sửa frontend. Commands và tất cả IDs: [TEST_REPORT](../bao_cao/context564/TEST_REPORT.md), [REGRESSION_IDS](../bao_cao/context564/REGRESSION_IDS.md).

Read-only published probe: 272 canonical blocks, 113 prose seeds; từ 5 broken packs xuống 0. 6 ranked fact groups giữ source row, closure/projection PASS ở K=5/36000; exhaustive có67groups, không nhầm6 là toàn nguồn. Giữ behavior ngoại lệ first-whole-group có sẵn trong prose.

## Runtime và blocker

Batch ASGI thực gọi upstream: E2E đoạn văn có embedding/Qdrant/reranker/Qwen, canonical prose verification và citation hợp lệ; batch cuối không còn409. TCP backend đang chạy cũng answered với 1 citation kiểm exact identity/hash/quote, ~10,98s; usage8Qwen calls success. Hello/thanks không retrieval/model; follow-up giữ AM-0007 và đổi năm2025 đúng.

**Reviewed Fact E2E chưa đạt**: câu chỉ tiêu SV/AM-0007/2026 và follow-up2025 vẫn insufficient_context. Probe trả39facts nhưng analysis thiếu entity code, table decision không bind AM-0007; có thêm rủi ro projection cùng metric cho cột chỉ tiêu và ghi nhận. Không sửa những phần độc lập ngoài scope hoặc bật evidence policy khác để ép PASS. Chưa nghiệm thu numeric benchmark. [LIVE_RAG_E2E_REPORT](../bao_cao/context564/LIVE_RAG_E2E_REPORT.md).

## An toàn và cleanup

Xác minh DB/MinIO/Qdrant local trước chạy; test DB nonce riêng, Storage riêng, port1 ngăn test chạm upstream thật. Read-only seals trước/sau khớp5collections/23bindings/2source revisions/27indexes/5assistants/13providerconfigs. Không sửa nguồn/hash/revision/index/publication.

DB test đã dọn bằng ownership guard; tổng11ownthreads/8gap records dọn, usage audit giữ. Xóa runtime test bị kiểm duyệt tự động chặn `blocked by policy`; giữ thư mục, không bypass hoặc retry bằng cách khác. Evidence riêng được giữ ở `backend/storage/context564`.

Agent không stage/commit/push/restart/deploy. HEAD có commit bên ngoài agent `32cdc36b` trong phiên, đã bảo toàn; vì vậy diff HEAD cuối không bao gồm toàn phần sửa đầu phiên.

## Bàn giao

[REVIEW_READY](../bao_cao/context564/REVIEW_READY.md) và 6 báo cáo/ID appendix. Bước tiếp theo có phạm vi riêng: entity code resolution và metric-role binding theo nguồn, rồi chạy lại đúng fact E2E; không cần tăng context Qwen để chữa lỗi packing đã tái hiện.
