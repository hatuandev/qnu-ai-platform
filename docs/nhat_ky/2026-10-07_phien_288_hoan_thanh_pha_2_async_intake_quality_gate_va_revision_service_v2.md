# NHẬT KÝ LÀM VIỆC — PHIÊN #288
**Thời gian**: 2026-10-07 | **Kỹ sư phụ trách**: Senior Full-Stack Architect & Enterprise AI Systems Specialist
**Mục tiêu chính**: Thực Hiện Phiên 3 (Pha 2) Kế Hoạch 11: Hoàn Thiện Quy Trình Tiếp Nhận Bất Đồng Bộ V2 (`POST /documents/intake` HTTP 202 Accepted), Cổng Thẩm Định Chất Lượng Quality Gate, Dịch Vụ Quản Lý Phiên Bản Bất Biến DocumentRevisionService & 100% Test Suite Pass.

---

## 1. Bối Cảnh & Mục Tiêu Phiên 3 (Pha 2)

Tiếp nối sự thành công của Phiên 2 (Pha 1) đã hoàn thành tầng Schema CSDL và migration Alembic có Safe Backfill, Phiên 3 bước vào triển khai toàn diện nghiệp vụ **Pha 2: Document Revision V2** theo đúng bản đồ kiến trúc ADR-011 và kế hoạch [`docs/ke_hoach/11_ke_hoach_trien_khai_quy_trinh_tiep_nhan_mot_lan_xuat_ban_tri_thuc_an_toan.md`](../ke_hoach/11_ke_hoach_trien_khai_quy_trinh_tiep_nhan_mot_lan_xuat_ban_tri_thuc_an_toan.md).

Mục tiêu cốt lõi của **Phiên 3 (Pha 2)** bao gồm:
1. **Quy trình tiếp nhận bất đồng bộ (Asynchronous Intake)**: Endpoint mới `POST /platform/v1alpha1/documents/intake` trả về mã trạng thái `HTTP 202 Accepted` (`AsyncUploadDocumentResponse`) kèm `job_id`, `revision_id`, tự động kiểm tra khử trùng lặp (Deduplication SHA-256) và điều phối công việc nền.
2. **Cổng kiểm định chất lượng tự động (Quality Gate Engine)**: Tự động đánh giá tính đầy đủ văn bản (`text_completeness`), mật độ chữ theo trang (`chars_per_page`), tỷ lệ bảo toàn cấu trúc bảng biểu (`table_preservation`), và phát hiện dấu hiệu vỡ font / Mojibake / scan mờ để đưa ra quyết định trạng thái (`passed` $\rightarrow$ `ready`, `warning` $\rightarrow$ `review_required`, `failed` $\rightarrow$ `failed`).
3. **Dịch vụ quản lý phiên bản bất biến (`DocumentRevisionService`)**:
   - Quản lý vòng đời chuỗi phiên bản (`v1`, `v2`, `...`), quan hệ lineage tự tham chiếu `based_on_revision_id`.
   - Pipeline phân tích và lưu vết provenance, page manifest, citation metadata.
   - Cơ chế hiệu đính Markdown (`update_revision_content`) và phê duyệt / từ chối (`submit_revision_review`) của chuyên viên biên tập trước khi xuất bản.
4. **Worker Task & ARQ Background Processing**: Đăng ký task `task_document_revision_parse` trong ARQ và background fallback runner.
5. **Đồng bộ tương thích ngược (Backward Compatibility)**: Đảm bảo endpoint cũ `POST /upload` vẫn hoạt động trơn tru với UI hiện tại, tự động sinh và quản lý song song bản ghi `DocumentRevision` v1.
6. **Kiểm thử tự động 100% & Linter Sạch**: Viết test suite toàn diện `test_document_revisions_lifecycle.py` và bảo đảm toàn bộ suite đạt 16/16 tests pass, 0 lỗi Ruff linter.

---

## 2. Các Kết Quả Hoàn Thành Trong Phiên

### 2.1. Động Cơ Thẩm Định Chất Lượng Tự Động (`backend/app/modules/documents/quality_gate.py`)
- Xây dựng hàm thẩm định cốt lõi: `evaluate_revision_quality(markdown, page_count, tables_count, file_size_bytes, ocr_engine)`.
- Các bài kiểm tra thẩm định:
  - **Text Completeness & Density**: Tính toán `chars_per_page`. Nếu $< 60$ chars/trang $\rightarrow$ gắn cờ cảnh báo `critically_low_text_density` (nghi ngờ scan mờ hoặc trượt OCR). Nếu text rỗng $\rightarrow$ đánh dấu thất bại `EMPTY_EXTRACTED_CONTENT`.
  - **Table Preservation**: Đếm số bảng Markdown `|---|` so với số bảng phát hiện từ bộ parser; phát hiện tình trạng mất bảng sau OCR.
  - **Mojibake & Character Corruption Detection**: Quét biểu thức chính quy các ký tự lạ `\ufffd`, `?{3,}`, non-printable characters. Nếu phát hiện $\rightarrow$ gắn cờ `mojibake_or_font_corruption_detected`.
- Quyết định trạng thái tổng thể:
  - `passed`: Văn bản đầy đủ, bố cục chuẩn $\rightarrow$ Tự động chuyển `ready` sẵn sàng xuất bản.
  - `warning`: Có cảnh báo mật độ chữ thấp hoặc dấu hiệu Mojibake $\rightarrow$ Chuyển `review_required` yêu cầu cán bộ rà soát.
  - `failed`: Lỗi nghiêm trọng $\rightarrow$ Chuyển `failed`.

### 2.2. Dịch Vụ Quản Lý Phiên Bản Bất Biến (`backend/app/modules/documents/revision_service.py`)
- **Tạo phiên bản khởi tạo `create_initial_revision`**: Tự động sinh `DocumentRevision` v1 cho tài liệu mới nạp.
- **Tạo phiên bản sửa đổi `create_new_revision`**: Tăng số hiệu `revision_no`, trỏ `based_on_revision_id` về con trỏ trước đó, bảo toàn lịch sử thay đổi bất biến.
- **Xử lý trích xuất `process_revision`**:
  - Đọc nhị phân từ S3, gọi `get_document_parser`.
  - Chuẩn hóa Unicode NFC (`clean_markdown_text`), bóc tách NĐ 30 (`extract_administrative_metadata`).
  - Render ảnh xem trước các trang PDF (`_render_pdf_previews`).
  - Đánh giá chất lượng qua `QualityGate` và cập nhật `page_manifest`, `citation_metadata`, `parse_provenance`.
  - Đồng bộ con trỏ `current_revision_id` và các trường legacy (`parsed_markdown`, `parse_status`) khi đạt `ready`.
- **Hiệu đính nội dung `update_revision_content`**: Cho phép chuyên viên sửa Markdown, tự động chuẩn hóa text, tính lại `canonical_hash`, tăng `lock_version`, ghi nhận nhật ký `human_reviews` vào `parse_provenance`, và thẩm định lại Quality Gate.
- **Phê duyệt bản sửa đổi `submit_revision_review`**:
  - Action `approve`: Chuyển trạng thái sang `ready`, nâng cấp con trỏ `doc.current_revision_id = rev.id`.
  - Action `reject`: Chuyển trạng thái sang `review_required`.

### 2.3. Pipeline Tiếp Nhận Bất Đồng Bộ V2 (`backend/app/modules/documents/intake_service.py`)
- Tính SHA-256 binary hash.
- Kiểm tra Deduplication: Nếu tài liệu đã có trong kho $\rightarrow$ trả về `AsyncUploadDocumentResponse` với `deduplicated=True` tức thì.
- Lưu trữ tệp an toàn vào MinIO S3 (`documents/originals/{file_hash}/{safe_name}`).
- Tạo `RepositoryDocument` và `DocumentRevision` v1.
- Tạo bản ghi `JobRecord` loại `document_revision_parse` trong PostgreSQL.
- Điều phối thực thi: Đẩy vào hàng đợi ARQ Redis `task_document_revision_parse`; nếu Redis worker tạm offline thì tự động kích hoạt async background runner dự phòng bảo đảm quy trình không bị nghẽn.
- Phản hồi HTTP 202 Accepted (`AsyncUploadDocumentResponse`).

### 2.4. Worker Tasks & Router Endpoints V2
- `backend/app/modules/jobs/service.py`: Đăng ký job type `"document_revision_parse": "task_document_revision_parse"` vào `ARQ_FUNCTIONS`.
- `backend/app/workers/tasks.py`: Xây dựng worker task `task_document_revision_parse(ctx, job_id)` theo dõi tiến trình và ghi kết quả thực tế vào `JobRecord`.
- `backend/app/modules/documents/router.py`:
  - `POST /platform/v1alpha1/documents/intake`: Endpoint V2 trả về HTTP 202 Accepted.
  - `GET /platform/v1alpha1/documents/{document_id}/revisions`: Danh sách lịch sử revisions.
  - `GET /platform/v1alpha1/documents/{document_id}/revisions/{revision_id}`: Chi tiết revision kèm manifests và quality report.
  - `PATCH /platform/v1alpha1/documents/{document_id}/revisions/{revision_id}/content`: Hiệu đính Markdown.
  - `POST /platform/v1alpha1/documents/{document_id}/revisions/{revision_id}/review`: Phê duyệt / từ chối revision.
  - `POST /platform/v1alpha1/documents/{document_id}/revisions/{revision_id}/retry`: Thử lại quy trình xử lý.

### 2.5. Kiểm Thử Unit Test Suite Đầy Đủ 100% Pass & Linter Sạch 0 Lỗi
- Tạo mới file kiểm thử: `backend/tests/test_document_revisions_lifecycle.py`:
  - `test_quality_gate_clean_markdown_passed`: Kiểm tra trường hợp Markdown hợp lệ đạt `passed`.
  - `test_quality_gate_empty_content_failed`: Kiểm tra trường hợp rỗng kích hoạt `failed` và `EMPTY_EXTRACTED_CONTENT`.
  - `test_quality_gate_low_density_and_mojibake_warning`: Kiểm tra cảnh báo mật độ chữ thấp và ký tự Mojibake.
  - `test_intake_service_upload_new_document`: Kiểm tra upload bất đồng bộ trả về 202 payload và tạo job.
  - `test_intake_service_deduplication`: Kiểm tra khử trùng lặp file trả về `deduplicated=True`.
  - `test_revision_content_review_and_approval_flow`: Kiểm tra luồng hiệu đính Markdown, tăng `lock_version` và phê duyệt nâng cấp lên `ready`.
  - `test_api_intake_and_revisions_routes`: Kiểm tra tích hợp router FastAPI qua HTTP Client (`POST /intake`, `GET /revisions`, `GET /revisions/{id}`).
- **Kết quả Pytest**: **16/16 tests PASSED 100%** trong 25.76s:
  ```
  tests\test_document_revisions_lifecycle.py ....... [ 43%]
  tests\test_document_revisions_schema.py ...        [ 62%]
  tests\test_document_repository.py ......           [100%]
  ======================= 16 passed, 1 warning in 25.76s ========================
  ```
- **Kết quả Ruff Linter**: **All checks passed (0 lint errors)**.

---

## 3. Danh Sách Tệp Đã Tạo Mới / Cập Nhật

1. [`backend/app/modules/documents/quality_gate.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/documents/quality_gate.py) — Động cơ kiểm tra chất lượng Quality Gate.
2. [`backend/app/modules/documents/revision_service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/documents/revision_service.py) — Dịch vụ quản lý vòng đời phiên bản nội dung bất biến và review.
3. [`backend/app/modules/documents/intake_service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/documents/intake_service.py) — Dịch vụ tiếp nhận tài liệu bất đồng bộ trả về HTTP 202 Accepted.
4. [`backend/app/modules/documents/router.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/documents/router.py) — Bổ sung endpoints `/intake` và nhóm API Revisions V2.
5. [`backend/app/modules/documents/service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/documents/service.py) — Đồng bộ luồng upload V1 tự động sinh và cập nhật `DocumentRevision` v1.
6. [`backend/app/modules/documents/schemas.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/documents/schemas.py) — Cập nhật type annotations cho phép `| None` an toàn trên các trường JSON.
7. [`backend/app/modules/documents/models.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/documents/models.py) — Bổ sung eager default constructor `__init__` cho `DocumentRevision`.
8. [`backend/app/modules/jobs/service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/jobs/service.py) — Đăng ký task `document_revision_parse` vào `ARQ_FUNCTIONS`.
9. [`backend/app/workers/tasks.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/workers/tasks.py) — Khai báo worker task `task_document_revision_parse`.
10. [`backend/app/core/exceptions.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/core/exceptions.py) — Bổ sung `ValidationException` chuẩn RFC 7807 (400 Bad Request).
11. [`backend/tests/test_document_revisions_lifecycle.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/test_document_revisions_lifecycle.py) — Test suite kiểm thử toàn diện Quality Gate, Async Intake, Review và HTTP Router.
12. [`docs/nhat_ky/2026-10-07_phien_288_hoan_thanh_pha_2_async_intake_quality_gate_va_revision_service_v2.md`](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/nhat_ky/2026-10-07_phien_288_hoan_thanh_pha_2_async_intake_quality_gate_va_revision_service_v2.md) — Nhật ký làm việc phiên #288.

---

## 4. Kế Hoạch Cho Phiên Kế Tiếp (Phiên 4 / Pha 3)

Sẵn sàng bước vào **Phiên 4 (Pha 3)**:
- Triển khai **Knowledge Binding & Staging Index Build V2**:
  - Tạo model và migration cho `knowledge_bindings`, `knowledge_vector_generations`, `knowledge_index_revisions`, `knowledge_index_activations`.
  - Xây dựng API:
    - `GET /collections/{id}/available-documents`: Lọc danh sách tài liệu từ Kho có revision `ready` khả dụng.
    - `POST /collections/{id}/bindings`: Tạo liên kết Kho Tri Thức theo revision cụ thể (`accepted` / `rejected` per item).
    - `GET /bindings/{id}/index-revisions`: Lịch sử các artifact index revision của binding.
  - Xây dựng Job dựng chỉ mục Staging `knowledge_index_build`: Sinh chunks/facts trong staging, batch embedding, upsert Qdrant với point ID deterministic `uuid5(generation:revision:chunk_id)`, kiểm tra Parity Gate trước khi chuyển `ready`.
