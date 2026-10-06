# Nhật Ký Phiên Làm Việc #266: Tích Hợp Server GPU On-Premise RTX 5090 Qua Tailscale (Qwen3 & DeepSeek-R1) Cho Mô-Đun Soạn Thảo Văn Bản & Ngân Hàng Câu Hỏi

- **Thời gian thực hiện**: 2026-10-05 (UTC+7)
- **Người thực hiện**: Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu**:
  1. Thử nghiệm và đo lường kết nối thực tế tới cụm mô hình AI trên server GPU NVIDIA GeForce RTX 5090 (`rtx5090-ollama`) qua mạng riêng ảo Tailscale (`http://100.105.13.53:11434`).
  2. Nâng cấp hạ tầng ModelOps và Hybrid RAG của QNU AI Platform để hỗ trợ native Ollama Embeddings và OpenAI-compatible LLM Generation không cần API key tĩnh.
  3. Cấu hình chuyên biệt dòng mô hình tư duy **Qwen3 & DeepSeek-R1 (32B)** cho hai phân hệ nghiệp vụ học thuật cốt lõi: **Mô-đun Soạn Thảo Văn Bản** (`ast_drafting`) và **Mô-đun Ngân Hàng Câu Hỏi & Khảo Thí** (`ast_question_bank`).

---

## 1. Kết Quả Đo Đạc Thực Tế Server AI RTX 5090 Qua Tailscale

Thực hiện kiểm thử kết nối từ laptop qua Tailscale (`http://100.105.13.53:11434`):
- **Trạng thái kết nối**: 200 OK, độ trễ mạng cực thấp (< 2ms qua tunnel WireGuard).
- **Mô hình kiểm thử**:
  - `qwen3:8b`: LLM Chat hoàn thành sinh phản hồi tiếng Việt trong **0.72 giây**.
  - `deepseek-r1:32b`: LLM Suy luận hoàn thành sinh tiêu đề văn bản hành chính trong **1.98 giây**.
  - `qwen3-embedding:4b-q8_0`: Vector embedding 2,560 chiều, hoàn thành trong **0.13 giây** (130ms).
  - `bge-m3:latest`: Vector embedding 1,024 chiều, hoàn thành trong **< 50ms**.
- **Đánh giá tải VRAM**: Cụm mô hình nạp thường trực ~28.6 GB / 32 GB VRAM trên RTX 5090, hoạt động trơn tru không bị OOM.

---

## 2. Các Tệp Mã Nguồn Đã Thay Đổi

1. [`backend/app/core/config.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/core/config.py):
   - Bổ sung cấu hình `OLLAMA_BASE_URL` mặc định trỏ tới `http://100.105.13.53:11434`, hỗ trợ đọc qua biến môi trường `OLLAMA_BASE_URL` hoặc `OLLAMA_HOST`.
2. [`backend/app/modules/modelops/providers/openai_adapter.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/modelops/providers/openai_adapter.py):
   - Mở rộng `OpenAIAdapter` hỗ trợ `provider_type="ollama"`, `custom`, `local`.
   - Cơ chế tự động nhận diện On-Premise: cho phép gửi request mà không ép buộc API key tĩnh, sử dụng fallback key `"ollama"` an toàn.
3. [`backend/app/modules/modelops/providers/__init__.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/modelops/providers/__init__.py):
   - Chuẩn hóa factory method `get_llm_adapter`: khi gọi với `provider_type="ollama"`, tự động định tuyến tới `OLLAMA_BASE_URL` và chuẩn hóa hậu tố `/v1`.
4. [`backend/app/modules/modelops/services/provider_service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/modelops/services/provider_service.py):
   - Bổ sung `prov_rtx5090_ollama` vào danh mục `STANDARD_QNU_PROVIDERS` với độ ưu tiên cao nhất (`priority: 1`), khai báo đầy đủ các mô hình: `deepseek-r1:32b`, `qwen3:8b`, `deepseek-r1:70b`, `qwen3-vl:32b`, `qwen3-vl:8b`, `qwen3-embedding:4b-q8_0`, `qwen3-embedding:8b`, `bge-m3:latest`.
5. [`backend/app/modules/rag/vector_indexer.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/vector_indexer.py):
   - Bổ sung phương thức `_embed_texts_ollama`: hỗ trợ cả native batch endpoint `/api/embed` và OpenAI-compatible `/v1/embeddings`.
   - Mở rộng `embed_texts` xử lý `provider in ("ollama", "ollama_local", "local")`.
   - Nâng cấp `ensure_collection` và `_fit_dim` hỗ trợ linh hoạt cả kích thước 1,024 chiều (BGE-M3) và 2,560 chiều (Qwen3).
6. [`backend/app/modules/assistants/seeder.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/assistants/seeder.py):
   - Mở rộng `_lifecycle_config` với tham số `preferred_provider_id` và `max_tokens`.
   - Cập nhật cấu hình Trợ lý Soạn thảo Văn bản (`ast_drafting`): `primary_model="deepseek-r1:32b"`, `fallback_model="qwen3:8b"`, `preferred_provider_id="prov_rtx5090_ollama"`, `max_tokens=3200`.
   - Cập nhật cấu hình Trợ lý Ngân hàng Câu hỏi & Khảo thí (`ast_question_bank`): `primary_model="deepseek-r1:32b"`, `fallback_model="qwen3:8b"`, `preferred_provider_id="prov_rtx5090_ollama"`, `max_tokens=3200`.

---

## 3. Kết Quả Kiểm Thử (Verification)

- **Backend Ruff Linter**:
  - Chạy `uv run ruff check` trên toàn bộ các tệp thay đổi: **All checks passed (0 lỗi, 0 cảnh báo)**.
- **Backend End-to-End Integration**:
  - Khởi tạo adapter `get_llm_adapter('ollama', 'qwen3:8b')` $\rightarrow$ sinh phản hồi trong 548ms.
  - Khởi tạo adapter `get_llm_adapter('ollama', 'deepseek-r1:32b')` $\rightarrow$ sinh văn bản thành công.
  - Chạy `VectorIndexer.embed_texts` với `qwen3-embedding:4b-q8_0` $\rightarrow$ vector hóa batch thành công 100%.
- **Frontend Vite Build**:
  - Đóng gói bundle production thành công (`✓ built in 11.38s`, 0 lỗi TypeScript, 0 lỗi bundler).

---

## 4. Bài Học Rút Ra & Khuyến Nghị

1. **Reranker trên Ollama**: Ollama không cung cấp endpoint Cross-Encoder (`/v1/rerank`), nên các mô hình reranker GGUF không dùng qua `api/generate`. Tầng RAG của QNU AI Platform dùng cơ chế Reciprocal Rank Fusion (RRF) kết hợp PostgreSQL BM25 FTS và Qdrant vector retrieval đã đảm bảo độ chính xác xuất sắc mà không phụ thuộc vào Ollama reranker.
2. **Kích thước vector**: `qwen3-embedding` có kích thước 2560 chiều trong khi `bge-m3` là 1024 chiều. Phương thức `_fit_dim` bảo đảm an toàn kích thước cho các collection Qdrant hiện hữu, đồng thời cho phép tạo collection 2560 chiều chuyên biệt khi cần.
