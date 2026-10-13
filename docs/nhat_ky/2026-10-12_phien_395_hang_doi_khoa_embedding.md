# Phiên #395 — Chờ khóa embedding và kiểm tra xuất bản hàng loạt

## Mục tiêu

Sửa lỗi nạp nhiều nguồn cùng lúc với một khóa vLLM; trả lời có cần hàng đợi cho xuất bản hàng loạt không. Áp dụng các skill Clean Code, Backend, ModelOps, RAG và Frontend/Admin cho nhãn chờ.

## Thay đổi

- `provider_key_rotation_service.py`: KeyAcquireResult.busy; đếm khóa còn hợp lệ/đủ quota, tách khóa đang leased/locked khỏi invalid/inactive/exhausted. acquire_wait polling async 0.5s với deadline cấu hình PROVIDER_QUEUE_TIMEOUT_SECONDS (mặc định120s), không giữ transaction khi ngủ; không lấy khóa giả hoặc bỏ kiểm tra quota. Release nếu cập nhật progress sau acquire bị hủy/lỗi.
- `model_runtime_resolver.py`: embedding/reranker dùng acquire_wait, giữ nguyên provider/model chỉ định. Lỗi hết deadline riêng MODEL_PROVIDER_KEY_BUSY (503).
- `leased_execution.py`: busy được phân loại transient theo cause chain, dùng recovery/backoff/giới hạn attempt hiện hữu; không retry vô hạn.
- `runtime_key_lease.py`: heartbeat30s gia hạn credential trong các batch embedding dài và khi chờ capacity; mất lease dừng tác vụ.
- `vector_indexer.py`: heartbeat cho embedding API, giải phóng khóa khi bị cancel ở nhánh vLLM/OpenAI-compatible.
- Frontend types/vector-workflow: đọc job.phase có sẵn từ JobResponse, nhãn Chờ embedding khi waiting_embedding; vẫn pending và không cho xuất bản.
- Regression: test_runtime_key_queue.py, opt-in test_runtime_key_queue_postgres.py, vector-workflow.test.ts.

## Thuật toán và giới hạn

Giữ lease độc quyền theo credential, chờ bất đồng bộ dựa trên trạng thái DB chung, kết hợp ARQ durable jobs và recovery sẵn có. Không cần schema/migration hay thêm khóa. Đây không phải FIFO nghiêm ngặt: các worker cạnh tranh lease theo polling; số tác vụ chạy được vẫn bị giới hạn bởi pool khóa và capacity AI. Deadline/backoff tránh treo vô hạn. Khóa thật sự invalid/exhausted vẫn báo lỗi.

## Xuất bản

Đọc generation_publish_service: kiểm tra tất cả nguồn/index/artifact, kích hoạt staging vector đã có, sau đó khóa collection for_update, refresh và CAS index_epoch + tập source revisions trước commit pointer chung. Không gọi embedding lại; chưa cần hàng đợi GPU/worker riêng. Nếu hai yêu cầu xuất bản cùng kho cạnh tranh, yêu cầu stale trả409 thay vì ghi đè; đây là khóa/CAS, không phải FIFO queue. Giữ nguyên luồng và không xuất bản nguồn người dùng.

## Xác minh

- Regression trước sửa:4fail đúng thiếu busy/acquire_wait; sau sửa bộ trọng tâm cuối32passed (bao gồm heartbeat, hủy, DB down, timeout, ModelOps, worker, vector workflow).
- PostgreSQL thật:20 tác vụ/1 credential thử nghiệm,20completed, peak giữ khóa1, usage20, lease được giải phóng; invalid không chờ. Tạo provider/key tạm UUID, dọn theo đúng UUID bằng cascade sau test, không dùng hoặc sửa khóa thật và không gọi AI.
- Ruff toàn backend đạt, có cảnh báo quyền đọc thư mục test cũ. Biome3fileFE đạt;5FEtests đạt; npm run build (Vite + tsc) exit0.
- Full backend trước khi thêm heartbeat regression/Postgres opt-in:977passed/11failed/2skipped, các lỗi nằm trong baseline dispatcher export, publishing legacy/canary/GC, reconciliation, auth role. Không tuyên bố full suite sạch. Test heartbeat thêm sau đó đạt trong bộ32.
- git diff --check đạt. Lần chạy test DB trong sandbox bị interpreter AccessDenied; chạy ngoài sandbox được phép đã đạt.

## Bàn giao

Chưa restart BE/FE/worker, retry nguồn cũ, reset, xuất bản hay chỉnh provider người dùng. Người dùng chạy lại make dev để worker nhận code mới rồi chỉ nạp lại nguồn lỗi; không cần upload/OCR lại. Các nguồn đang dùng không đổi. Cập nhật README nhật ký, PROJECT_CONTEXT và WORK_LOG.
