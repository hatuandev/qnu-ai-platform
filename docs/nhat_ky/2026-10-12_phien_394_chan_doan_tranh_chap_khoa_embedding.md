# Phiên #394 — Chẩn đoán tranh chấp khóa embedding

## Mục tiêu và phạm vi

Điều tra lỗi nạp vector sau khi người dùng duyệt tài liệu. Chỉ đọc code và PostgreSQL trong transaction READ ONLY; không sửa runtime, khóa, trạng thái job, retry, xuất bản hay restart.

## Bằng chứng

- Provider `prov_rtx5090_vllm` có đúng một khóa quản lý, active/is_active=true, quota_limit=null, usage_tokens=47256; cooldown/lease/last_error_code=null, consecutive_failures=0 tại thời điểm kiểm tra.
- Audit 15:40:47–15:40:56 UTC ngày 12/10 ghi liên tiếp selected/success, không có sự kiện invalid/rate_limited/exhausted trong kết quả gần nhất. Đây là 22:40 giờ địa phương.
- Index revisions failed có failure_detail đúng thông báo không còn khóa khả dụng; jobs cùng đợt cũng ghi lỗi này, retryable chưa được đánh dấu.
- `ProviderKeyRotationService.acquire` loại khóa đang có lease, dùng SKIP LOCKED; không có khóa tự do thì trả managed=true/lease=None ngay.
- `ModelRuntimeResolver.resolve` chuyển kết quả đó thành MODEL_PROVIDER_KEYS_UNAVAILABLE (503), không phân biệt khóa bận với khóa hỏng/hết quota.
- `VectorIndexer.index_chunks` resolve/lease khóa trước `embed_texts`; semaphore Redis `provider_slot` chỉ nằm trong embed_texts nên không điều tiết tranh chấp khóa trước đó. Lease giữ suốt các batch embedding của nguồn.
- Worker `is_retryable_failure` chưa có MODEL_PROVIDER_KEYS_UNAVAILABLE. Wrapper VECTOR_INDEXING_FAILED giữ cause nhưng bộ phân loại vẫn không nhận lỗi này là tạm thời.

## Kết luận và đề xuất (chưa triển khai)

Lỗi điều phối đồng thời: nhiều job cạnh tranh một khóa độc quyền; tác vụ đến khi khóa bận thất bại trước khi gửi yêu cầu embedding. Không phải lỗi OCR/duyệt, không có bằng chứng khóa sai hoặc hết quota.

Đề xuất phân biệt busy/no-valid-key, chờ có giới hạn và backoff khi busy; lấy capacity trước khi lease khóa hoặc điều phối hàng đợi chung, tránh giữ khóa khi chờ capacity. Retry chỉ lỗi bận/transient, không tự retry khóa invalid/quota. Bảo đảm release khi success/error/cancel, heartbeat cho lease dài; UI hiện chờ embedding thay vì hết khóa. Nếu cho phép nhiều request trên cùng credential, cần thiết kế quota reservation/concurrency riêng, không bỏ khóa DB tùy tiện. Kiểm thử nhiều job với một khóa, crash/cancel/timeout, 401/429 và parity/idempotency; chỉ nạp lại nguồn lỗi, không bóc tách lại hay reset DB.

## Xác minh và tài liệu thay đổi

- Đã đối chiếu code và trạng thái DB/audit thật, không gọi API inference tạo chi phí.
- Không chạy Ruff/Pytest/Vite vì không thay đổi mã nguồn ứng dụng.
- Cập nhật nhật ký này, README nhật ký, PROJECT_CONTEXT và WORK_LOG.
- Một truy vấn chẩn đoán ban đầu tham chiếu updated_at không tồn tại ở index revisions; đã sửa SELECT. Console Windows cần Python -X utf8 để in tiếng Việt.
