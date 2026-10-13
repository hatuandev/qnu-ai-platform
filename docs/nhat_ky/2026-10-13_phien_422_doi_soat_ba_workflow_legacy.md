# Phiên 422 — Đối soát ba workflow legacy chặn sao lưu

## Ủy quyền và phạm vi

Sau kết luận phiên 421, người dùng xác nhận “ok bạn làm đi”: cho phép chuyển đúng ba workflow HTTP 500 cũ từ running sang failed, giữ dữ liệu/lịch sử, không replay chatbot hoặc tools. Không sửa runtime, không reset DB/Redis, không restart dịch vụ, không tạo hay khôi phục backup mới.

Áp dụng hướng dẫn backend và clean-code cho thao tác vận hành có rủi ro: preflight read-only, exact IDs/identity guards, row lock, conditional update và transaction atomic; dừng/rollback khi có thay đổi không khớp bằng chứng. Không thêm cơ chế tự dọn mọi workflow legacy hoặc bỏ guard backup.

## Các bản ghi đã đối soát

| Execution | Correlation | Bằng chứng HTTP 500 |
|---|---|---|
| `0f200a3a-30dc-4736-b1b9-159277ae387c` | `corr_9de8b577196d` | `admissions_eval413.json`, nhật ký 413 |
| `c7d8e6f3-e4a7-4ee7-a644-d81c2c11a303` | `corr_51bdaa5dd6da` | `admissions_eval415.json`, nhật ký 415 |
| `8bb61da6-22e0-44ec-ab2e-d1f69ca23ba1` | `corr_a22538683359` | `admissions_eval415.json`, nhật ký 415 |

Preflight xác nhận tenant_qnu / admissions-assistant / ast_admissions; status running, completed_at/error_message/deadline null, node_execution_count và saved nodes 0; chưa có legacy_reconciliation. Correlation và created_at khớp bằng chứng phiên 421.

## Thay đổi trong DB

- Dùng kết nối asyncpg, shared advisory lock maintenance để không ghi trong lúc backup giữ exclusive lock.
- Transaction với lock_timeout 5 giây, `FOR UPDATE` đúng ba ID; kiểm tra lại scope/identity/trạng thái trước ghi.
- Cập nhật duy nhất `status='failed'`, `completed_at`, `error_message` và thêm `runtime_profile.legacy_reconciliation`. Điều kiện UPDATE giữ chính xác ID, correlation, created_at, tenant/assistant/workflow, trạng thái/deadline/node như preflight; trả đúng từng ID hoặc rollback toàn bộ.
- Error ghi `WORKFLOW_LEGACY_RECONCILED: observed HTTP 500; user-approved closure without replay`.
- Audit ghi session 422, người thực hiện Codex theo ủy quyền người dùng (không giả actor đăng nhập), timestamp UTC, evidence_file/correlation, reason, no_replay=true và previous status/completed_at/error_message/runtime profile digest. Đây là đối soát lỗi đã quan sát, không khẳng định stack trace gốc của ba lượt cũ.
- Commit đúng **3 hàng**, completed_at **2026-10-13 13:29:42.293116 UTC** (20:29:42 giờ Việt Nam). Đây là thời điểm đóng bản ghi sau đối soát, không giả là thời điểm lỗi HTTP 500 ban đầu.

## Kiểm chứng

- Trước commit: input/output digests không đổi, bỏ audit mới khỏi runtime_profile cho digest khớp profile gốc; node count và tổng số workflow không đổi. Không xóa hội thoại, execution/nodes hoặc kết quả cũ.
- Sau commit: kết nối độc lập/transaction read-only xác nhận 3/3 status failed, completed_at và audit session422/no_replay=true.
- **Remaining running workflows = 0; pending/running/retryable jobs = 0** tại thời điểm kiểm tra. Blocker hiện tại của backup đã được gỡ; tác vụ mới phát sinh sau kiểm tra vẫn có thể chặn theo guard bình thường.
- Không có thay đổi source Backend/Frontend. Không chạy Ruff/Pytest/Vite vì đây là đối soát dữ liệu vận hành theo exact IDs, không phải sửa code; kiểm chứng bằng preflight, conditional transaction invariants và post-commit readback. Không thay kết quả kiểm thử phiên 420 bằng cam kết backup corpus thật.

## Bàn giao

Người dùng F5/Làm mới trang Sao lưu, tạo bản mới bằng mật khẩu tự giữ. Không cần restart hoặc reset DB cho thay đổi trạng thái này. Các backup failed trước đây được giữ nguyên, không tự retry bằng mật khẩu lưu. Chưa tạo bản backup corpus thật thành công; nếu có lỗi ở bước sau, đọc chi tiết bản mới và xử lý đúng nguyên nhân.

Đã đồng bộ nhật ký README, PROJECT_CONTEXT và WORK_LOG. Bài học: reconciliation legacy cần bằng chứng và ủy quyền theo exact IDs, không gán deadline giả hoặc đổi trạng thái hàng loạt để né guard an toàn.
