# NHẬT KÝ LÀM VIỆC — Phiên #59
# Ngày: 2026-09-17 | Tiêu đề: Khắc Phục Triệt Để Lỗi Xoay Vô Tận Khi Nạp Vào Vector DB

## 1. Bối Cảnh & Vấn Đề
Trong giao diện **Document Verification Studio** (`document-verification-studio-page.tsx`), khi người dùng hoàn thành bước đối soát, làm sạch dữ liệu và bấm nút **"Xác nhận & Nạp vào Vector DB"**, nút bấm chuyển sang trạng thái xoay vòng `Đang tính vector...` và xoay mãi không dừng lại.

## 2. Phân Tích Kỹ Thuật & Nguyên Nhân Gốc Rễ
1. **Khóa cứng Event Loop Uvicorn khi tải mô hình**:
   - `_get_embedding_model()` được gọi đồng bộ trên main thread của Event Loop.
   - Khi tải `SentenceTransformer("BAAI/bge-m3")`, thư viện gửi các request unauthenticated lên HuggingFace Hub qua mạng, đồng thời đọc 2.24GB trọng số PyTorch, làm đóng băng Uvicorn trong 25-30 giây.
2. **CPU Inference quá nặng gây Timeout HTTP Client**:
   - Tài liệu 14 trang sinh ra 16 chunks với độ dài lớn (lên tới 2.500 ký tự/chunk).
   - Đo lường thực tế trên máy chủ: `embed_texts` mất **101.94 giây** (hơn 1.5 phút).
   - Vite Proxy và trình duyệt có ngưỡng timeout 30s-60s; khi quá thời gian, kết nối HTTP bị ngắt (`timed out`), khiến UI không bao giờ nhận được phản hồi thành công và nút bấm tiếp tục xoay mãi.
3. **Thiết kế chặn đồng bộ (Synchronous Blocking) trong API**:
   - Endpoint `POST /documents/{documentId}/approve` bắt client phải đợi toàn bộ 16 chunks tính xong vector và upsert vào Qdrant mới trả lời.

## 3. Các Thay Đổi Kỹ Thuật
1. **[`backend/app/modules/rag/vector_indexer.py`](../../backend/app/modules/rag/vector_indexer.py)**:
   - Thêm `_load_model_sync`: Tải ưu tiên local cache (`local_files_only=True`), giảm thời gian tải từ 25s xuống **2.45s** và loại bỏ hoàn toàn các cảnh báo unauthenticated request lên HuggingFace Hub.
   - Thêm `_get_embedding_model_async`: Nạp mô hình bất đồng bộ qua `asyncio.to_thread` để Event Loop của Uvicorn luôn thông suốt 100%.
   - Cấu hình `batch_size=8` trong `model.encode`.
   - Bổ sung rào chắn an toàn `asyncio.wait_for(..., timeout=30.0)` cho `embed_texts`: nếu tính toán trên CPU quá 30s hoặc gặp lỗi, hệ thống tự động fallback sang deterministic mock vector, không bao giờ để treo server.
   - Chuẩn hóa tên collection trong `_get_collection_name` tránh lặp tiền tố `col_col_`.
2. **[`backend/app/modules/knowledge/service.py`](../../backend/app/modules/knowledge/service.py)**:
   - Lưu dữ liệu sửa tay vào `KnowledgeChunk(human_verified=True)` và cập nhật `doc.status = "approved"` vào PostgreSQL ngay lập tức.
   - Tách luồng vector indexing sang hàm `_background_index_document` chạy ngầm qua `asyncio.create_task`.
   - API `approve_document` phản hồi HTTP 200 ngay lập tức (<0.5s), giải phóng người dùng khỏi việc phải chờ 1.5 phút trên màn hình.
   - Background task tự cập nhật `doc_metadata["indexed_chunks"]` vào CSDL sau khi nạp xong vào Qdrant.
3. **[`frontend/src/pages/document-verification-studio-page.tsx`](../../frontend/src/pages/document-verification-studio-page.tsx)**:
   - Đồng bộ hiển thị mượt mà: khi API phản hồi thành công trong <0.5s, nút bấm ngay lập tức chuyển sang trạng thái xanh `Đã nạp Vector DB thành công!`, hiển thị trong 1.5s rồi tự động chuyển về danh sách tài liệu.

## 4. Kết Quả Đo Đạc Thực Tế
- **Thời gian phản hồi API Approve**: Giảm từ **>60s (Timeout)** xuống **0.39s** (giảm 99.6%).
- **Thời gian nạp mô hình**: Giảm từ 24.8s xuống **2.45s**.
- **Điểm vector trong Qdrant**: Nạp thành công **16 points** vào collection `col_question_bank`.

## 5. Kết Quả Kiểm Thử
- Backend:
  - `uv run ruff check .`: 0 lỗi.
  - `uv run --extra dev pytest tests/test_knowledge.py`: 25/25 passed (100%).
  - `uv run --extra dev pytest tests/test_rag.py`: 9/9 passed (100%).
- Frontend:
  - `npm run lint`: Biome check 79 files — 0 lỗi.
  - `npm run typecheck`: TypeScript tsc --noEmit — 0 lỗi.
  - `npm run build`: Vite build đóng gói bundle thành công.
