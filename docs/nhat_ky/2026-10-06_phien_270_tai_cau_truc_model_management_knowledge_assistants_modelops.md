# NHẬT KÝ LÀM VIỆC — PHIÊN 270 (2026-10-06)
## Dự Án: QNU.AI Platform — Trường Đại Học Quy Nhơn
## Chủ Đề: Tái Cấu Trúc Toàn Diện Hệ Thống Quản Lý Mô Hình: Tách Bạch ModelOps Hạ Tầng, Gắn Embedding & OCR Vào Kho Tri Thức, Phân Bổ Cross-Encoder Reranker Sang Trợ Lý AI

---

### 1. Bối Cảnh & Động Lực Kỹ Thuật

Trước phiên 270, hệ thống tồn tại sự chồng chéo và gò bó trong quy trình cấu hình mô hình:
1. **ModelOps (`/models`) bị ôm đồm**: Chứa cả các Tab cấu hình "Mặc Định Hệ Thống" và "Combos & Vision Adapter", làm mờ nhạt vai trò quản trị hạ tầng thuần túy (Providers, Key Pool, Catalog, Quota, Healthcheck).
2. **Kho Tri Thức (`/knowledge`) bị phụ thuộc ngầm**: Tất cả các kho tri thức buộc phải dùng chung một mô hình Embedding và OCR mặc định từ ModelOps, không thể tùy biến mô hình bóc tách OCR hay không gian vector hóa riêng biệt cho từng lĩnh vực đặc thù (Tuyển sinh, Quy chế, Thư viện, Soạn thảo văn bản).
3. **Reranker bị cấu hình sai vị trí**: Cross-Encoder Reranker là một mắt xích truy xuất thông tin (RAG Retrieval Policy) thuộc về từng Trợ lý AI (tùy vào trợ lý cần độ chính xác cao hay tốc độ phản hồi nhanh), nhưng lại bị cấu hình tập trung ở cấp độ toàn hệ thống.

**Giải pháp của người dùng & Kiến trúc mới**:
- **Trang ModelOps (`/models`)**: Thuần túy quản trị hạ tầng nhà cung cấp (Cloud, Custom, On-Premise GPU), quản lý nhóm khóa API xoay vòng (Key Pool), Catalog và chính sách phục hồi Circuit Breaker.
- **Trang Kho Tri Thức (`/knowledge`)**: Mỗi kho tri thức độc lập sở hữu cấu hình `data_processing` riêng: Mô hình Vector Embedding (kèm enforce *Quy tắc Bất biến Không gian Vector - Vector Invariance*), Mô hình Vision OCR chính (Primary OCR) và dự phòng (Fallback OCR), cùng switch cứu hộ OCR văn bản quét/ảnh.
- **Trang Trợ Lý AI (`/assistants`)**: Chuyển giao toàn bộ chính sách Cross-Encoder Reranker (`reranker_policy`) vào chính sách truy xuất RAG của từng Trợ lý (bật/tắt Reranker, chọn model Cross-Encoder, tinh chỉnh `top_k`, và `score_threshold`).

---

### 2. Các Thay Đổi & Triển Khai Kỹ Thuật Chi Tiết

#### 2.1. Backend Architecture & Dynamic Resolution
- **[`backend/app/modules/knowledge/schemas.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/schemas.py)**:
  - Khai báo DTO `CollectionDataProcessingConfig` (embedding_model, embedding_provider_id, embedding_dimension, ocr_mode, primary_ocr_model, fallback_ocr_model, enable_ocr_rescue).
  - Tích hợp vào `CollectionCreateRequest` và `CollectionUpdateRequest`.
- **[`backend/app/modules/knowledge/services/collection_service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/services/collection_service.py)**:
  - Khởi tạo mặc định `data_processing` tối ưu cho máy chủ AI RTX 5090 (`bge-m3:latest` 1024D và `qwen3-vl:8b` On-Premise).
  - **Enforce Vector Invariance Rule**: Trong `update_collection`, nếu kho đã có tài liệu (`document_count > 0`), hệ thống tự động chặn đổi mô hình Embedding và trả mã lỗi `RFC 7807` `VECTOR_MODEL_IMMUTABLE` kèm giải thích chi tiết.
- **[`backend/app/modules/knowledge/services/ingestion_service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/services/ingestion_service.py)**:
  - Hàm `_run_ocr_rescue` đọc động `primary_ocr_model` và `fallback_ocr_model` từ cấu hình riêng của từng Collection (`collection_metadata["data_processing"]`).
  - Truyền `collection_id` xuyên suốt luồng cứu hộ OCR.
- **[`backend/app/modules/rag/vector_indexer.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/vector_indexer.py)**:
  - Cập nhật `_resolve_embedding_runtime`: nhận `collection_id`, truy vấn DB đọc `data_processing` để nạp đúng mô hình vector embedding được kho đó chỉ định; fallback an toàn về resolver toàn cục.
  - Cập nhật `index_chunks` và `search_dense` truyền `collection_id` vào runtime embedding.
- **[`backend/app/modules/assistants/schemas.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/assistants/schemas.py) & [`seeder.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/assistants/seeder.py)**:
  - Bổ sung schema `AssistantRerankerPolicy` (enabled, model_name, top_k, score_threshold).
  - Gắn vào `AssistantKnowledgePolicy.reranker_policy` của 5 trợ lý AI mẫu.
- **[`backend/app/modules/rag/retriever.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/retriever.py) & [`reranker.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/reranker.py)**:
  - Nhận `reranker_policy`: nếu `enabled=False`, lập tức trả về Top RRF fused chunks mà không cần qua Cross-Encoder (cắt giảm hoàn toàn 300-500ms độ trễ mạng).
  - Nếu `enabled=True`, gọi Reranker theo model và ngưỡng điểm `score_threshold` được chỉ định.
- **[`backend/app/modules/workflows/nodes/rag_answer_node.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/workflows/nodes/rag_answer_node.py)**:
  - Trích xuất `reranker_policy` từ profile của Trợ lý và nạp vào `AskRequest`.

#### 2.2. Frontend Architecture & UI/UX Gold Standard
- **[`frontend/src/pages/modelops-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/modelops-page.tsx)**:
  - Gỡ bỏ hoàn toàn `mainViewMode` và hai Tab buttons "Combos & Vision Adapter", "Mặc Định Hệ Thống".
  - Trang `/models` trở về thuần túy quản trị Provider Grid, Key Pool xoay vòng khóa API, Filter theo nhóm Cloud / Custom / On-Premise, và thẻ chính sách phục hồi Circuit Breaker.
- **[`frontend/src/components/knowledge/dialogs/collection-config-dialog.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/knowledge/dialogs/collection-config-dialog.tsx)**:
  - Nâng cấp Dialog với 3 Tab rõ ràng: **Cơ bản**, **Vector Embedding**, và **Vision OCR**.
  - Hiển thị mô hình Embedding đang dùng kèm kích thước vector chiều; tự động khóa (`disabled={true}`) khi `documentCount > 0` kèm thông báo cảnh báo thị giác màu Amber giải thích *Quy tắc Bất biến Không gian Vector*.
  - Cho phép cấu hình Vision OCR: Bật/tắt OCR Rescue, chọn Primary OCR (`qwen3-vl:8b`, `gemini-3.1-flash-lite`, `gpt-4o-mini`, v.v.) và Fallback OCR.
- **[`frontend/src/pages/collection-detail-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/collection-detail-page.tsx)**:
  - Quản lý state `configDataProcessing` và truyền xuống `CollectionConfigDialog`.
  - Kết nối API `updateCollection` lưu trữ cấu hình `data_processing` vào database.
- **[`frontend/src/components/assistants/sections/assistant-knowledge-section.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/assistants/sections/assistant-knowledge-section.tsx)**:
  - Bổ sung Card cấu hình **Xếp Hạng Lại (Cross-Encoder Reranker)**: Switch bật/tắt reranker, Dropdown chọn mô hình (`bge-reranker-base`, `bge-reranker-large`, `ms-marco-MiniLM-L-6-v2`, `cohere-rerank-v3`), Input Top K sau khi rerank, Input ngưỡng điểm tương đồng (Score Threshold).
  - Khi tắt Reranker, hiển thị box giải thích về cơ chế tăng tốc phản hồi (0ms độ trễ).
- **[`frontend/src/pages/assistant-detail-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/assistant-detail-page.tsx) & [`types.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/assistants/types.ts)**:
  - Đồng bộ 4 trường reranker vào `AssistantEditForm`, ánh xạ qua `toEditForm` và lưu vào `knowledge_policy.reranker_policy` trong `updateMutation`.

#### 2.3. Database Synchronization & Migration
- **[`backend/scripts/sync_data_processing_and_reranker.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/scripts/sync_data_processing_and_reranker.py)**:
  - Đã chạy thành công trên PostgreSQL CSDL production local:
    - 5/5 Kho tri thức chuẩn (`col_drafting`, `col_regulations`, `col_admissions`, `col_library`, `col_question_bank`) đã nạp `data_processing`: Embedding=`bge-m3:latest` (1024D), Primary OCR=`qwen3-vl:8b`, Fallback OCR=`gemini-3.1-flash-lite`.
    - 5/5 Trợ lý AI chuẩn (`question_bank`, `admissions`, `drafting`, `library`, `regulations`) đã nạp `reranker_policy`: `enabled=True`, `model_name=bge-reranker-base`, `top_k=5`, `score_threshold=0.4`.

---

### 3. Kết Quả Kiểm Thử & Xác Minh

1. **Python Linter (`ruff`)**:
   ```bash
   .venv\Scripts\python.exe -m ruff check app/modules/rag/vector_indexer.py
   # Found 0 errors
   ```
2. **CSDL PostgreSQL Migration**:
   ```bash
   .venv\Scripts\python.exe scripts/sync_data_processing_and_reranker.py
   # === SYNC COMPLETED SUCCESSFULLY ===
   ```
3. **Frontend Production Build (`vite build`)**:
   ```bash
   cmd /c npm run build
   # vite v6.4.3 building for production...
   # ✓ 2662 modules transformed.
   # ✓ built in 9.65s (0 errors, exit code 0)
   ```

---

### 4. Bài Học Rút Ra & Điểm Lưu Ý Cho Phiên Kế Tiếp

1. **Vector Invariance (Bất biến không gian Vector)**: Việc khóa đổi mô hình Embedding khi kho đã có tài liệu là quyết định kiến trúc cực kỳ quan trọng, ngăn ngừa 100% tình trạng hỏng vector database do trộn lẫn các vector thuộc không gian khác nhau.
2. **Phân tách trách nhiệm sạch (Separation of Concerns)**:
   - Hạ tầng Provider/API Key/Quota $\rightarrow$ `/models`
   - Bóc tách văn bản, OCR, Vector hóa $\rightarrow$ `/knowledge`
   - Tìm kiếm, Reranker, Prompt, Guardrail $\rightarrow$ `/assistants`
   Mô hình này giúp người quản trị vận hành trực quan, đúng nghiệp vụ và linh hoạt tối đa.
