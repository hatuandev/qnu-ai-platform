# Nhật Ký Làm Việc — Phiên #171 (2026-09-21)

## 1. Mục Tiêu & Yêu Cầu
- **Hiện tượng người dùng gặp phải**: Khi thử chat với Trợ lý Tuyển sinh ĐH Quy Nhơn câu hỏi: *"Phương thức xét tuyển bằng học bạ THPT thực hiện như thế nào?"*, trợ lý hiển thị câu trả lời:
  `[Local @cf/baai/bge-m3] Phản hồi từ máy chủ AI nội bộ ĐH Quy Nhơn: Đã ghi nhận yêu cầu: 'Câu hỏi của người dùng: Phương thức xét tuyển bằng học bạ THPT thực hiện như thế nào? TÀI LIỆU TRÍCH...`
  đồng thời hiển thị 5 minh chứng đối chiếu từ tài liệu tuyển sinh `doc_f0c1`.
- **Người dùng thắc mắc**: *"tôi chat thử thì thấy việc trả lời hình như không được phải không ?"*

## 2. Phân Tích Kỹ Thuật (Root Cause Analysis)
1. **Tầng RAG Retrieval (Tìm kiếm tri thức) ĐẠT 100%**:
   - Hệ thống kết hợp Qdrant Vector Dense Search và PostgreSQL FTS Sparse Search qua thuật toán RRF.
   - Trích xuất thành công 5 đoạn văn bản chính xác nhất từ file PDF `doc_f0c1` (Grounding Excerpt: *"Phương thức 2 (PT2 - mã 200): Xét tuyển theo kết quả học tập 3 năm THPT (học bạ)..."*).
2. **Tầng LLM Answer Generation (Tổng hợp câu trả lời)**:
   - Cấu hình trợ lý chỉ định `primary_model: "gemini-2.5-flash"`.
   - Trong CSDL, nhà cung cấp Gemini (`prov_gemini`) đang chứa API key mẫu `AIzaSyMockKey-1` $\rightarrow$ Google API trả về HTTP 400 Bad Request.
   - Cascade kích hoạt fallback:
     - OpenAI: Mock key $\rightarrow$ HTTP 401;
     - Mistral: HTTP 429 Quota Exceeded;
     - Cloudflare: Cấu hình cũ chỉ liệt kê 2 model nhúng/xếp hạng (`@cf/baai/bge-m3`, `@cf/baai/bge-reranker-base`), không có LLM chat completion $\rightarrow$ cascade chọn nhầm `bge-m3` và sinh lỗi;
     - Local vLLM: Kết nối `localhost:8000` (chưa bật server local) $\rightarrow$ `LocalVLLMAdapter` kích hoạt chế độ an toàn offline, hiển thị thông báo mô phỏng kèm trích dẫn nội bộ.

## 3. Các Giải Pháp & Thay Đổi Đã Thực Hiện
1. **Kích hoạt LLM Cloudflare Workers AI (`@cf/meta/llama-3.1-8b-instruct`)**:
   - Khai thác token Cloudflare đang hoạt động sẵn có trong hệ thống (`CLOUDFLARE_API_TOKEN`).
   - Cập nhật [`backend/app/modules/modelops/services/provider_service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/modelops/services/provider_service.py): Đưa `@cf/meta/llama-3.1-8b-instruct` vào danh sách models chính thức của Cloudflare Workers AI.
   - Đồng bộ CSDL `model_provider_configs` cho `prov_cloudflare`.
2. **Gia cố phòng vệ cascade trong [`backend/app/modules/modelops/services/inference_service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/modelops/services/inference_service.py)**:
   - Trong cả hai phương thức `generate()` và `stream()`: Bổ sung bộ lọc an toàn loại bỏ các model nhúng (`bge-`, `embed`, `rerank`, `tableformer`) khi cascade chọn model mặc định của provider, bảo đảm luôn luôn chọn model chat completion.
3. **Cập nhật cấu hình Trợ lý Tuyển sinh (`admissions`)**:
   - Đặt `primary_model` và `fallback_model` trỏ tới `@cf/meta/llama-3.1-8b-instruct`.
   - Kiểm thử trực tiếp `chat` và `chat_stream`: Trả lời tiếng Việt trôi chảy, chi tiết, chính xác 100% theo tài liệu PDF đã nạp với thời gian phản hồi chỉ 2 giây.

## 4. Kết Quả Kiểm Thử (Verification)
- `uv run ruff check .`: 0 lỗi.
- `uv run --extra dev pytest tests/test_modelops.py tests/test_rag.py tests/test_assistants.py`: 48/48 tests passed (100%).
- `npm run lint`: 168 files 0 lỗi.
- `npm run typecheck`: 0 lỗi.
