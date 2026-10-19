# Phiên551 — Kiểm thử lại Qwen32K và Luna

Người dùng tăng Qwen server lên32K, thử Luna HTTP200 và yêu cầu chạy lại. Áp dụng ModelOps và clean-code cho thay đổi helper nhỏ; không sửa application code hoặc defaults. Giữ dirty diff549/550.

Helper `backend/scripts/verify_json_output_contract.py` thêm `--chat-model` chọn active model từ chain, no-fallback probe kiểm provider/requested model; ghi rõ router response model. Dossier tại [báo cáo551](../bao_cao/context551/VALIDATION_REPORT.md).

Actual `chat-qwen`PASS(exit0),509,98ms; `chat-luna`PASS(exit0),4935,17ms; cả hai không fallback. `live-table`FAIL(exit1): Qwen200/16338input/1191output/JSON-schemaPASS, binder row scope ambiguity. `live-api`FAIL(exit1): Qwen200/16312input/1587output/JSON-schemaPASS, binder unit mismatch;22packets planned/1sent. Không có lỗi context cũ trong hai gói đã gửi, nhưng chưa kiểm21packet còn lại. Effective contractprompt_only, chưa native strict verified. Human review/applyNOT_RUN. Scoped Ruff1helperPASS; full currentNOT_RUN, historical54918FAIL/2336PASS/17skip giữ nhãn lịch sử.

Audit DB/MinIO/Qdrant mới; shared local DB chỉREADONLY, bản sao encrypted ModelOps vào DB test có ownership và LocalStorage riêng. Xuất metadata, xóa DB/runtime test và xác nhận; defaults hash/URL/timeout/activity trước/sau giữ nguyên. Không production migration, appcodefix, commit/push/restart/deploy/reparse nguồn thật/approve/index/publish. Cần xử lý chất lượng selector/source binding trước nghiệm thu; chỉ tăng context chưa hoàn tất annotation.
