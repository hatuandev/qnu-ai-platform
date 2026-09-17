# NHẬT KÝ LÀM VIỆC — Ngày: 2026-09-17
## Tiêu đề: Tính năng Thiết lập Model Mặc định Hệ thống (Embedding, Reranker, OCR) cho Kho Tri Thức & RAG

### 1. Bối Cảnh & Yêu Cầu Người Dùng
Người dùng yêu cầu:
> *"đối với mấy model embđing hay reranker của Cloudflare hay local tôi muốn thêm 1 tính năng mặc định để áp dụng vào khi sử dung những chắc năng như là kho tri thức chẳng hạn"*

Mục tiêu là cho phép người quản trị cấu hình mô hình nào (Cloudflare Workers AI vs Local CPU) sẽ được dùng làm **mặc định hệ thống** cho 3 vai trò:
1. **Default Embedding Model**: Tự động áp dụng khi nạp, chuẩn hóa và vector hóa tài liệu trong Kho Tri Thức (ví dụ `@cf/baai/bge-m3` qua Cloudflare Edge 1.0s vs `BAAI/bge-m3` qua SentenceTransformers Local CPU).
2. **Default Reranker Model**: Tự động áp dụng khi Trợ lý AI thực hiện truy xuất Hybrid RAG (ví dụ `@cf/baai/bge-reranker-base` qua Cloudflare vs `rrf_fallback` qua Local Reciprocal Rank Fusion).
3. **Default OCR Model**: Tự động áp dụng cho quy trình bóc tách tài liệu scan (ví dụ `mistral-ocr-latest` vs Local PyMuPDF/Docling).

---

### 2. Các Thay Đổi Kỹ Thuật (Key Changes)

#### A. Backend Architecture & API (`backend/app/modules/modelops/`)
1. **Data Schemas ([schemas.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/modelops/schemas.py))**:
   - Khai báo DTO `ModelOption`: Thông tin provider, model_name, category (`cloud`, `local`, `custom`).
   - Khai báo `SystemModelDefaults` và `SystemModelDefaultsUpdate`: Lưu trữ 3 cặp `provider_id` + `model_name` cho embedding, reranker, ocr.
   - Khai báo `SystemModelDefaultsResponse`: Trả về cấu hình hiện tại kèm danh sách các model có sẵn theo từng vai trò (`available_embeddings`, `available_rerankers`, `available_ocrs`).
   - Khai báo `SetDefaultModelRequest`: DTO hỗ trợ gán nhanh 1 model cụ thể làm default theo vai trò (`role: embedding | reranker | ocr`).

2. **Core Service Logic ([service.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/modelops/service.py))**:
   - `get_system_model_defaults`: Tự động duyệt qua toàn bộ provider active trong DB và presets để bóc tách danh sách các mô hình khả dụng theo từ khóa (`bge`, `embed`, `rerank`, `ocr`, provider types). Trả về record `system_model_defaults` từ DB (hoặc fallback config an toàn).
   - `update_system_model_defaults`: Lưu cấu hình vào PostgreSQL (bảng `model_provider_configs` với ID `system_model_defaults`) và đồng bộ trực tiếp vào runtime `settings.EMBEDDING_PROVIDER`, `settings.EMBEDDING_MODEL`, `settings.RERANKER_PROVIDER`, `settings.RERANKER_MODEL`.
   - `set_provider_model_as_default`: Xử lý gán nhanh một model của một provider làm default cho vai trò tương ứng.

3. **REST Endpoints ([router.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/modelops/router.py))**:
   - `GET /platform/v1alpha1/modelops/defaults`: Lấy cấu hình defaults và model khả dụng.
   - `PUT /platform/v1alpha1/modelops/defaults`: Cập nhật cấu hình defaults.
   - `POST /platform/v1alpha1/modelops/providers/{provider_id}/set-default`: Gán nhanh model của provider làm mặc định.

4. **Lifespan Startup Sync ([main.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/main.py))**:
   - Tự động nạp cấu hình `system_model_defaults` từ PostgreSQL vào `settings` khi ứng dụng khởi động.

#### B. Frontend UI/UX & TanStack Integration (`frontend/src/`)
1. **API Client ([api-client.ts](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/services/api-client.ts))**:
   - Khai báo kiểu dữ liệu `ModelOption`, `SystemModelDefaults`, `SystemModelDefaultsResponse`.
   - Thêm các methods `getSystemModelDefaults()`, `updateSystemModelDefaults()`, `setProviderModelAsDefault()`.

2. **Giao diện Quản trị ModelOps ([modelops-page.tsx](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/modelops-page.tsx))**:
   - Thêm Card điều khiển cao cấp **"Mô Hình Mặc Định Hệ Thống (Active System Defaults)"** ngay trên danh sách Provider.
   - Bố trí 3 cột chọn lựa tương ứng:
     * **Embedding (Kho Tri Thức & Vector hóa)**: Dropdown chọn Cloudflare Edge (`@cf/baai/bge-m3`) hoặc Local CPU (`BAAI/bge-m3`).
     * **Reranker (Truy xuất RAG & Xếp hạng)**: Dropdown chọn Cloudflare Reranker (`@cf/baai/bge-reranker-base`) hoặc Local Fallback (`rrf_fallback`).
     * **OCR & Trích xuất Tài liệu**: Dropdown chọn Mistral OCR hoặc Docling Engine.
   - Tích hợp badge **"★ Default Embedding"**, **"★ Default Reranker"**, **"★ Default OCR"** và nút thao tác nhanh **"Đặt Default"** trực tiếp trên từng tag mô hình trong Provider Detail sheet/dialog.

3. **Phản ánh Trực quan trên Kho Tri Thức ([knowledge-page.tsx](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/knowledge-page.tsx) & [collection-detail-page.tsx](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/collection-detail-page.tsx))**:
   - Thay thế chuỗi tĩnh bằng dữ liệu thực `systemDefaults?.default_embedding_model`.
   - Hiển thị icon động: tia sét `Zap` màu vàng hổ phách cho mô hình Cloudflare Workers AI Edge vs icon `Cpu` màu teal cho mô hình Local SentenceTransformers.
   - Hiển thị thanh trạng thái tổng quan các mô hình mặc định trên Header của trang Kho Tri Thức kèm nút bấm chuyển hướng nhanh tới `/modelops`.

---

### 3. Kết Quả Kiểm Thử (Verification)

#### Backend Verification
```bash
uv run ruff check .
# Kết quả: All checks passed! (0 lỗi)

uv run --extra dev pytest -v tests/test_modelops.py
# Kết quả: 13/13 passed (100% pass) bao gồm test_system_model_defaults_api

uv run --extra dev pytest -v tests/test_rag.py tests/test_knowledge.py
# Kết quả: 34/34 passed (100% pass, không suy suyển RAG hay ingestion)
```

#### Frontend Verification
```bash
npm run lint
# Kết quả: Biome check 83 files, 0 lỗi

npm run typecheck
# Kết quả: tsc --noEmit, 0 lỗi

npm run build
# Kết quả: Vite build production bundle thành công (index.html, CSS 113.90 kB, JS 1369.50 kB)
```
