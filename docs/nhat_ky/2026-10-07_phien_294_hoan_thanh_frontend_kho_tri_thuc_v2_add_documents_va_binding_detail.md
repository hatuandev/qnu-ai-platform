# NHẬT KÝ LÀM VIỆC — PHIÊN #294 (2026-10-07)
## Thực Hiện Phiên 9 Kế Hoạch 11: Hoàn Thành Master-Detail Deep Routing Cho Kho Tri Thức V2 — Trang Thêm Tài Liệu Từ Kho (`/add-documents`) & Trang Chi Tiết Binding Chuyên Sâu (`/documents/:bindingId`)

---

### 1. Thông Tin Phiên Làm Việc
- **Thời gian**: 2026-10-07 21:40 – 22:15 (UTC+7)
- **Kỹ sư phụ trách**: AI Senior Full-Stack Architect
- **Mục tiêu**: Hoàn tất mục tiêu **Phiên 9** theo [Kế hoạch 11](../../docs/ke_hoach/11_ke_hoach_trien_khai_quy_trinh_tiep_nhan_mot_lan_xuat_ban_tri_thuc_an_toan.md) và [ADR-011](../../docs/adr/ADR-011-immutable-document-revisions-and-safe-knowledge-publishing.md):
  1. Triển khai kiến trúc **Master-Detail Deep Routing** (AGENTS.md Mục 4.5) cho Kho Tri Thức V2: Tách biệt trang danh sách tổng quan (`CollectionDetailPage`) với các trang nghiệp vụ chuyên sâu, sở hữu URL phân cấp rõ ràng (`/knowledge/:collectionId/add-documents` và `/knowledge/:collectionId/documents/:bindingId`).
  2. Xây dựng **Trang Thêm Tài Liệu Từ Kho Tập Trung** (`AddDocumentsPage`): Tìm kiếm, phân loại theo trạng thái liên kết, chọn nhiều tài liệu, tùy biến chiến lược phân đoạn (Clause-based, Semantic, Recursive, Markdown Header) và kích hoạt sticky action bar tạo bindings hàng loạt.
  3. Xây dựng **Trang Chi Tiết Binding Chuyên Sâu** (`BindingDetailPage`): Bento Grid 4 KPIs, 3 Tabs nghiệp vụ (Index Revisions & Rollback $O(1)$, Trình duyệt Chunks Inspector, Thông tin Nguồn & Metadata NĐ 30/2020/NĐ-CP).
  4. Mở rộng Backend: Bổ sung endpoint phân trang `GET /knowledge/bindings/{binding_id}/chunks` phục vụ Chunk Inspector.
  5. Bảo đảm Quality Gate: 13/13 tests `test_knowledge_publishing_v2.py` pass 100%, Ruff 0 lỗi, Biome linter 0 lỗi, TypeScript typecheck 0 lỗi.

---

### 2. Các Thay Đổi Chi Tiết

#### 2.1. Mở Rộng Backend: Endpoint Lấy Danh Sách Chunks Cho Binding (`schemas.py`, `binding_service.py`, `service.py`, `router.py`)
- **DTOs (`backend/app/modules/knowledge/schemas.py`)**:
  * `KnowledgeChunkItemResponse`: Trả về thông tin chi tiết từng chunk (`id`, `chunk_index`, `content`, `section`, `token_count`, `qdrant_point_id`, `created_at`).
  * `BindingChunksListResponse`: Bao gồm `items: list[KnowledgeChunkItemResponse]`, `total: int`, `page: int`, `page_size: int`, `index_revision_id: str | None`.
- **Dịch vụ (`backend/app/modules/knowledge/services/binding_service.py`)**:
  * Triển khai hàm `list_binding_chunks(db, binding_id, page=1, page_size=20, index_revision_id=None)`:
    - Tìm kiếm `KnowledgeBinding`. Nếu không truyền `index_revision_id`, tự động lấy revision đang `active` của binding.
    - Truy vấn danh sách `KnowledgeChunk` theo `index_revision_id`, sắp xếp tuần tự theo `chunk_index asc`.
    - Hỗ trợ phân trang chuẩn `offset` / `limit` và đếm tổng số chunks `total`.
- **Router & Facade (`router.py`, `service.py`)**:
  * Thêm endpoint `GET /knowledge/bindings/{binding_id}/chunks`:
    - Nhận query params: `page` (default 1), `page_size` (default 20, max 100), `index_revision_id` (tùy chọn).
    - Trả về DTO `BindingChunksListResponse`.

#### 2.2. Mở Rộng Frontend Types & API Client (`types/knowledge.ts`, `services/knowledge-api.ts`)
- **Types (`frontend/src/types/knowledge.ts`)**:
  * `KnowledgeChunkItem`: Định nghĩa cấu trúc chunk của binding.
  * `BindingChunksResponse`: Cấu trúc phản hồi phân trang từ API.
  * `RollbackIndexRevisionRequest`: Khai báo request hoàn tác index revision.
- **API Client (`frontend/src/services/knowledge-api.ts`)**:
  * `getBindingChunks(bindingId, params)`: Gọi endpoint `GET /knowledge/bindings/{binding_id}/chunks`.
  * `rollbackIndexRevision(bindingId, payload)`: Gọi endpoint `POST /knowledge/bindings/{binding_id}/rollback`.

#### 2.3. Xây Dựng Trang Thêm Tài Liệu Chuyên Biệt (`AddDocumentsPage`)
- **Vị trí**: `frontend/src/features/knowledge/add-documents-page.tsx`.
- **Route**: `frontend/src/routes/knowledge.$collectionId.add-documents.tsx` (`/knowledge/:collectionId/add-documents`).
- **Tính năng nổi bật**:
  * Header với thanh điều hướng quay lại (`ArrowLeft`), breadcrumb phân cấp rõ ràng `Kho Tri Thức / [Tên Bộ Sưu Tập] / Thêm Tài Liệu`.
  * Thanh công cụ tìm kiếm tức thì theo tiêu đề / số hiệu / tên tệp và bộ lọc trạng thái (Tất cả, Chưa liên kết, Đã liên kết).
  * Panel cấu hình Chunking Strategy toàn cục cho đợt gắn liên kết:
    - Lựa chọn Strategy: Kế thừa mặc định bộ sưu tập, `ClauseBasedChunker` (Quy chuẩn ĐH Quy Nhơn), `SemanticChunker`, `RecursiveCharacterChunker`, `MarkdownHeaderChunker`.
    - Cấu hình Chunk Size (ký tự) và Chunk Overlap.
  * Bảng tài liệu sẵn sàng từ Kho Tập Trung với checkbox chọn từng tài liệu hoặc chọn tất cả (`Select All`).
  * Huy hiệu trạng thái trực quan: `Đã liên kết vào kho này`, `Chưa liên kết`, thể thức văn bản hành chính NĐ 30, số hiệu, ngày ban hành, kích thước file.
  * Sticky Bottom Action Bar nổi khối (`motion.div`): Hiển thị số lượng tài liệu đã chọn, switch "Tự động kích hoạt (Auto-activate)", nút Hủy và nút "Thêm vào Bộ Sưu Tập" kèm spinner khi mutation đang xử lý.

#### 2.4. Xây Dựng Trang Chi Tiết Binding Chuyên Sâu (`BindingDetailPage`)
- **Vị trí**: `frontend/src/features/knowledge/binding-detail-page.tsx`.
- **Route**: `frontend/src/routes/knowledge.$collectionId.documents.$bindingId.tsx` (`/knowledge/:collectionId/documents/:bindingId`).
- **Thiết kế chuẩn Master-Detail Deep Routing (AGENTS.md)**:
  * **Header & Action Bar**:
    - Nút Back quay lại Kho tri thức, Breadcrumb đầy đủ.
    - Tiêu đề tài liệu, tên file gốc, badge trạng thái liên kết (`Hoạt động`, `Chưa lập chỉ mục`, `Lỗi`), badge revision đang kích hoạt (Rev #X).
    - Nhóm nút hành động: "Dựng Staging Index Mới" (icon `Play`), "Gỡ Liên Kết" (icon `Trash2`, variant destructive outline).
  * **Bento Grid 4 KPI Metrics**:
    1. *Phiên Bản Nguồn Hiện Tại*: Hiển thị mã revision tài liệu (`drev_...`), định dạng file, dung lượng.
    2. *Chỉ Mục Phục Vụ (Active Index)*: Phiên bản index active, ngày kích hoạt, trạng thái phục vụ tìm kiếm.
    3. *Kích Thước Dữ Liệu*: Tổng số chunks, số lượng vector points đã nạp vào Qdrant.
    4. *Tính Toàn Vẹn & Parity Gate*: Trạng thái khớp 100% giữa DB và Qdrant, bảo vệ chống lệch dữ liệu.
  * **3 Tabs Nghiệp Vụ Chuyên Sâu**:
    - **Tab 1: Lịch Sử Index Revisions & Rollback $O(1)$**:
      * Bảng danh sách toàn bộ các phiên bản chỉ mục (v1, v2, v3...) của binding này.
      * Thể hiện rõ: Trạng thái (`active`, `superseded`, `staged`, `pruned`, `failed`), chiến lược chunking áp dụng, pipeline version, số chunks, hash nguồn, thời gian tạo.
      * Thao tác trên từng phiên bản:
        - Nút **Kích Hoạt (Promote)**: Khi bản ghi ở trạng thái `staged` đã pass Parity Gate, mở dialog xác nhận hoán đổi con trỏ nguyên tử (Atomic Pointer Swap CAS).
        - Nút **Hoàn Tác (Rollback $O(1)$)**: Khi bản ghi ở trạng thái `superseded` nằm trong retention window, mở dialog xác nhận trỏ ngay lập tức về bản cũ mà không cần tính toán lại vector embedding.
    - **Tab 2: Trình Duyệt Chunks (Chunk Inspector)**:
      * Thanh tìm kiếm nội dung chunk hoặc lọc theo điều khoản (`section`).
      * Danh sách các chunk hiển thị thứ tự `chunk_index`, trích đoạn văn bản, số tokens, ID vector point trên Qdrant.
      * Hỗ trợ click vào bất kỳ chunk nào để mở **Modal Chi Tiết Chunk** toàn màn hình: xem toàn văn nội dung chunk, tiêu đề section, thẻ metadata thể thức NĐ 30, copy văn bản.
    - **Tab 3: Thông Tin Nguồn & Thể Thức NĐ 30/2020/NĐ-CP**:
      * Bảng thông tin chi tiết về tài liệu gốc trong Kho Tập Trung:
        - Số hiệu văn bản, trích yếu, ngày ban hành, cơ quan ban hành.
        - Hash SHA-256 đối soát tính toàn vẹn.
        - Đường dẫn lưu trữ đối tượng trên MinIO S3 (`storage_path`).
        - Nút mở xem tệp gốc.
  * **Hộp Thoại Điều Khiển Nghiệp Vụ (Dialogs)**:
    - Dialog Dựng Staging Index Mới: Tùy chỉnh strategy, chunk size, overlap, auto-activate.
    - Dialog Promote Revision: Giải thích cơ chế Parity Gate 100% và ghi nhận lý do kiểm toán.
    - Dialog Instant Rollback $O(1)$: Giải thích cơ chế bảo vệ Rollback window và ghi nhận lý do hoàn tác.
    - Dialog Xác nhận Gỡ Liên Kết (Detach): Cảnh báo rõ ràng chỉ gỡ liên kết khỏi kho tri thức này, hoàn toàn không xóa tài liệu trong Kho Tập Trung.

#### 2.5. Tích Hợp Điều Hướng Tại `CollectionBindingsTab`
- Cập nhật [`frontend/src/components/knowledge/tabs/collection-bindings-tab.tsx`](../../frontend/src/components/knowledge/tabs/collection-bindings-tab.tsx):
  * Thêm nút "+ Thêm Tài Liệu Từ Kho" trên Action Toolbar dẫn sang `/knowledge/:collectionId/add-documents`.
  * Thêm nút "Chi Tiết" (icon `ArrowUpRight`) ở mỗi hàng tài liệu trong bảng dẫn trực tiếp sang `/knowledge/:collectionId/documents/:bindingId`.

---

### 3. Kết Quả Kiểm Thử Toàn Diện (Quality Gate)

#### 3.1. Kiểm Thử Backend (Pytest & Ruff)
- **Unit Test Mới**: `test_list_binding_chunks_service_and_api` trong `test_knowledge_publishing_v2.py`:
  * Kiểm thử service `binding_service.list_binding_chunks` với pagination và filter `index_revision_id`.
  * Kiểm thử API endpoint `GET /knowledge/bindings/{binding_id}/chunks` trả về HTTP 200 OK và đúng cấu trúc DTO.
- **Kết quả Pytest**: **13/13 tests PASSED 100%** trong 47.13s:
  * `test_models_v2_instantiation_defaults`: PASSED
  * `test_chunk_and_collection_expansion_fields`: PASSED
  * `test_get_available_documents_success`: PASSED
  * `test_create_bindings_success`: PASSED
  * `test_create_bindings_already_bound_skips`: PASSED
  * `test_create_bindings_missing_revision_fails`: PASSED
  * `test_build_staging_index_success`: PASSED
  * `test_build_staging_index_empty_text_fails`: PASSED
  * `test_promote_index_revision_atomic_pointer_swap`: PASSED
  * `test_promote_index_revision_invalid_status_rejects`: PASSED
  * `test_api_get_available_documents`: PASSED
  * `test_api_create_bindings_endpoint`: PASSED
  * `test_list_binding_chunks_service_and_api`: PASSED
- **Ruff Linter**: `All checks passed!` (0 lỗi, 0 cảnh báo).

#### 3.2. Kiểm Thử Frontend (TypeScript Typecheck & Biome Linter)
- **TypeScript Typecheck (`bun x tsc --noEmit`)**:
  * Kiểm tra toàn bộ mã nguồn Frontend: **Exit code 0 — 0 LỖI BIÊN DỊCH**!
  * Khắc phục triệt để typing cho TanStack Router khi thêm route mới bằng type-safe path casting.
- **Biome Linter (`bun x @biomejs/biome check`)**:
  * Quét 2 tệp giao diện mới `add-documents-page.tsx` và `binding-detail-page.tsx`.
  * **Exit code 0 — 0 errors, 0 warnings**!
  * 100% tuân thủ quy chuẩn semantic elements (dùng `<span>` thay thế các thẻ `<label>` không có target input, optional chaining `c.section?.toLowerCase()`, các nút hành động hỗ trợ đầy đủ phím truy cập a11y).

---

### 4. Bảng Tổng Hợp Tệp Mã Nguồn Đã Thay Đổi / Tạo Mới

| STT | Tệp | Trạng thái | Mô tả |
| :---: | :--- | :---: | :--- |
| 1 | `backend/app/modules/knowledge/schemas.py` | Cập nhật | Bổ sung DTOs `KnowledgeChunkItemResponse` và `BindingChunksListResponse` |
| 2 | `backend/app/modules/knowledge/services/binding_service.py` | Cập nhật | Bổ sung hàm nghiệp vụ `list_binding_chunks` hỗ trợ phân trang và lọc revision |
| 3 | `backend/app/modules/knowledge/service.py` | Cập nhật | Bổ sung facade method `list_binding_chunks` |
| 4 | `backend/app/modules/knowledge/router.py` | Cập nhật | Thêm endpoint `GET /knowledge/bindings/{binding_id}/chunks` |
| 5 | `backend/tests/test_knowledge_publishing_v2.py` | Cập nhật | Bổ sung unit test `test_list_binding_chunks_service_and_api` (13/13 passed) |
| 6 | `frontend/src/types/knowledge.ts` | Cập nhật | Bổ sung TypeScript types cho chunks và rollback request |
| 7 | `frontend/src/services/knowledge-api.ts` | Cập nhật | Bổ sung API client methods `getBindingChunks` và `rollbackIndexRevision` |
| 8 | `frontend/src/features/knowledge/add-documents-page.tsx` | **Tạo mới** | Giao diện toàn màn hình Thêm tài liệu từ kho, tìm kiếm, cấu hình chunking, sticky bar |
| 9 | `frontend/src/routes/knowledge.$collectionId.add-documents.tsx` | **Tạo mới** | TanStack Router file route cho `/knowledge/:collectionId/add-documents` |
| 10 | `frontend/src/features/knowledge/binding-detail-page.tsx` | **Tạo mới** | Giao diện Master-Detail chuyên sâu 4 KPIs, 3 Tabs (Revisions/Rollback, Chunks Inspector, NĐ 30) |
| 11 | `frontend/src/routes/knowledge.$collectionId.documents.$bindingId.tsx` | **Tạo mới** | TanStack Router file route cho `/knowledge/:collectionId/documents/:bindingId` |
| 12 | `frontend/src/components/knowledge/tabs/collection-bindings-tab.tsx` | Cập nhật | Thêm nút "+ Thêm Tài Liệu Từ Kho" và nút "Chi Tiết" điều hướng sang 2 trang mới |

---

### 5. Kết Luận & Hướng Tiếp Theo
- **Kết luận**: Phiên 9 theo lộ trình Kế hoạch 11 đã được triển khai hoàn chỉnh 100%. Nền tảng hiện sở hữu trải nghiệm quản trị tri thức chuyên nghiệp, tuân thủ nghiêm ngặt Master-Detail Deep Routing của AGENTS.md, cung cấp đầy đủ công cụ kiểm soát phiên bản chỉ mục bất biến, kiểm định Parity Gate, hoán đổi nguyên tử Atomic Pointer Swap và hoàn tác $O(1)$ tức thì.
- **Chỉ số Quality Gate**:
  * Backend Pytest: 13/13 passed 100%
  * Backend Ruff Linter: 0 lỗi
  * Frontend TypeScript: 0 lỗi (`tsc --noEmit` pass)
  * Frontend Biome Linter: 0 lỗi, 0 warnings
