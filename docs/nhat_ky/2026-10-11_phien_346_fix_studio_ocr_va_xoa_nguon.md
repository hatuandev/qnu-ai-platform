# Phiên #346 — Sửa Studio OCR và xóa nguồn Kho tri thức

## Phạm vi

Xử lý 6 findings review #345 và bổ sung nút xóa nguồn. Tạm dừng RAG/DAG theo yêu cầu; không sửa mã RAG/DAG trong phiên này, không đụng qnu-sso, reset DB, migration hay đổi khóa/provider của người dùng. Working tree đã có nhiều thay đổi từ các phiên trước, được giữ nguyên.

## Thay đổi

1. Studio dùng tọa độ left/top hoặc x/y từ backend; pixel đổi sang phần trăm theo kích thước trang thật, không đoán A4/vị trí/nhãn bằng từ khóa. Giữ ID, thứ tự đọc, toàn bộ nội dung và hai confidence; thiếu tọa độ không vẽ khung giả.
2. Tách Lưu và Duyệt. ID revision mới trả từ API được dùng để duyệt/tải lại; không ép trạng thái ready hay chạy thanh tiến trình embedding giả. Parent chọn đúng revision sau lưu.
3. Reparse giữ khóa hàng nguồn, đặt trước revision queued và durable JobRecord trong cùng transaction trước dispatch Redis. Worker đăng ký task riêng, khóa revision để chặn worker trùng, ghi lỗi/cancel vào revision; job lỗi không thay chỉ mục vector đang phục vụ.
4. Hiệu đính tạo revision mới, giữ dimensions/blocks theo số trang; đánh dấu alignment stale vì nội dung đã đổi, không tự dịch chuyển khung. Không bịa khung cho trang mới không có provenance.
5. Trang chi tiết mặc định xem revision mới nhất và có bộ chọn bản, query revision để mở lại; polling chỉ khi có bản đang xử lý. Không để active cũ che bản cần duyệt.
6. Mapper không cắt ngắn nội dung/đánh đồng text confidence với layout confidence; nút làm mới chỉ tải dữ liệu bố cục đã lưu và nói đúng hành vi, không giả chạy OCR.
7. Nút Xóa ở danh sách và chi tiết dùng ConfirmDialog. Backend khóa collection rồi binding, chặn xóa khi đang bóc tách/build, deactivate từng index revision đúng namespace vector generation, soft-detach và tăng epoch để vô hiệu cache. Giữ tệp Kho tài liệu, snapshot và lịch sử đối soát. Nếu Qdrant lỗi thì không commit DB/xác nhận thành công; thao tác remote không phải distributed transaction, retry có thể cần thiết.
8. Live probe phát hiện chọn PaddleOCR trực tiếp dùng adapter không có URL và báo nhầm thiếu khóa. Đã sửa phân giải active Paddle provider từ DB (ưu tiên provider mặc định phù hợp, sau đó priority), lấy nguyên model/endpoint/timeout. Thiếu provider fail-fast; đường chọn Paddle trực tiếp không fallback mock. Không đổi cấu hình server.

## Tệp liên quan

- Backend: knowledge `schemas.py`, `router.py`, services `source_ingestion_service.py`, `source_pages.py`, `source_reparse.py`, `binding_service.py`; jobs `service.py`; workers `tasks.py`, `arq_worker.py`; OCR `service.py`.
- Frontend: Studio workspace/canvas/inspector; source-detail; collection-bindings-tab; DeleteSourceButton; studio-mapper/studio-actions; knowledge-api và DTOs knowledge/studio-ocr.
- Tests: studio revision safety, source ingestion, workers, OCR ModelOps safety; hai test utilities Studio frontend; script live `backend/scripts/verify_studio_346.py`.

## Bằng chứng kiểm thử

- Regression explicit Paddle chạy fail trước sửa: OCR_PROVIDER_CREDENTIALS_MISSING. Sau sửa đường phân giải DB đạt; bổ sung case thiếu provider không fallback.
- Backend trọng tâm cuối phiên: **68 passed**, bao gồm OCR, immutable edit/review, queue/failure, delete/Qdrant failure, worker registration, provenance/chunking/publishing.
- Frontend utilities: **6 passed** (bbox phần trăm/pixel/invalid, ID mới, save-only và quality failure).
- Ruff toàn backend exit 0; có cảnh báo Access denied khi quét thư mục cũ. Biome 13 tệp phạm vi đạt. Vite build + TypeScript exit 0.
- Full pytest: **809 passed / 8 failed / 2 skipped** (trước khi thêm case thiếu Paddle provider cuối cùng, case này đã chạy trong 68 tests). 8 failures cùng nhóm cũ #345: 6 endpoint publishing/GC/canary/direct upload trả 403 với fixture quyền cũ, reconciliation legacy fixture, role AI.Admin vs admin. Chưa khẳng định toàn suite sạch.
- Lần full đầu có thêm 5 setup errors do quyền thư mục temp Windows; chạy lại với basetemp mới riêng trong storage đã hết setup errors. Không xóa thư mục temp cũ.
- Live script: PostgreSQL thật xác nhận hai queue đồng thời chỉ có một revision, một yêu cầu 409; **chỉ broker dispatch được thay bằng no-op để không gửi job vào worker cũ**. Sau đó gọi worker service trực tiếp với PaddleOCR/MinIO thật: PDF scan ít nhất 2 trang có bbox, ảnh trang 2 JPEG, edit giữ blocks, delete soft nguồn kiểm thử giữ snapshot. Fixture không có generation nên deactivate vector chỉ được phủ bằng unit test, không gọi Qdrant thật trong probe này.
- Đã dọn đúng collection/job rows tạo riêng bởi live script; không xóa snapshot hay tài liệu người dùng. Audit/cache OCR có thể được tạo theo luồng thật.

## Giới hạn và vận hành

- Chưa chạy browser E2E sau sửa trong phiên này, chưa kiểm chứng dispatch ARQ mới qua worker đang chạy hoặc xóa nguồn đã xuất bản với Qdrant thật.
- Cần khởi động lại worker (và API nếu không autoreload) để nhận task `task_knowledge_source_reparse`; không cần reset DB/migration.
- Theo skills clean-code và ingestion: sửa có phạm vi, bảo toàn provenance và test rủi ro transaction; tái sử dụng Button/ConfirmDialog theo skills frontend/admin.
- Bài học: adapter family availability không thay thế phân giải cấu hình ModelOps; báo lỗi thiếu khóa sai nguyên nhân có thể che lỗi wiring.
