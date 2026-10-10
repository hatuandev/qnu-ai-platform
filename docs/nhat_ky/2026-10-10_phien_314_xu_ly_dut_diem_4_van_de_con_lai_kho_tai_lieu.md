# Nhật Ký Phiên #314: Xử Lý Dứt Điểm 4 Vấn Đề Còn Lại Của Kho Tài Liệu Trước Khi Thiết Kế Quy Trình Kho Tri Thức

- **Thời gian**: 2026-10-10 12:30 (UTC+7)
- **Người thực hiện**: Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu**: Xử lý triệt để 4 vấn đề kỹ thuật còn lại của phân hệ Kho tài liệu (`RepositoryDocument`, `DocumentGroup`, `DocumentRevision`, `DocumentIntakeService`, `Legacy V1 Adapter`, `AttachGroupDialog`), bảo đảm độ tin cậy tuyệt đối trước khi bước sang giai đoạn thiết kế quy trình Kho tri thức.
- **Phạm vi nghiêm ngặt**:
  - Không sửa repository `qnu-sso`.
  - Không refactor ngoài phạm vi.
  - Không thay đổi các API không liên quan.
  - Không commit các file runtime trong `backend/storage/documents/`.

---

## 1. Chi Tiết Các Giải Pháp Kỹ Thuật

### 1.1. Sửa Race Condition Xóa Nhầm Object Khi Upload Đồng Thời (Vấn đề 1)
- **File**: `backend/app/modules/documents/intake_service.py`
- **Hiện tượng cũ**: Hai request đồng thời có cùng `(tenant_id, workspace_id, file_hash, safe_file_name)` sử dụng chung `storage_key`. Khi một request thua composite unique constraint, nhánh `except IntegrityError` gọi `storage_service.delete(storage_key)` trước khi truy vấn winner, dẫn đến nguy cơ xóa nhầm file vật lý hợp lệ của request thắng.
- **Giải pháp triệt để**:
  1. Trong nhánh `except IntegrityError`:
     - Lập tức thực thi `await db.rollback()` để giải phóng aborted transaction state.
     - Truy vấn winner document theo `(tenant_id, workspace_id, file_hash)` trước.
     - **Nếu tìm thấy winner**:
       - Tuyệt đối **không** gọi `storage_service.delete(storage_key)` (tuân thủ nguyên lý bất biến content-addressed storage: cùng SHA-256 là cùng nội dung byte, object của winner phải được bảo toàn).
       - Bổ sung membership vào Document Group một cách idempotent nếu request có `group_id` (kiểm tra `existing_mem` trước khi `db.add`).
       - Đọc revision thật từ CSDL (`current_revision_id` hoặc revision mới nhất) và truy vấn `JobRecord` đang hoạt động thật của revision đó.
       - Nếu winner không có revision hợp lệ: ném ngay lỗi RFC 7807 HTTP 409 `DOCUMENT_REVISION_INVALID`.
       - Tuyệt đối không sinh revision ID giả (`f"rev_{winner_doc.id}"`), số revision giả hay trạng thái giả.
       - Trả về DTO `AsyncUploadDocumentResponse` deduplicated hợp lệ với đúng revision status thật và job ID thật.
     - **Nếu không tìm thấy winner** (xác định transaction tạo tài liệu đã thất bại hoàn toàn): lúc này mới thực hiện compensation delete `storage_key`.
- **Regression tests**:
  - `test_concurrent_intake_winner_exists_does_not_delete_storage_object`: Hai request cạnh tranh, winner tồn tại -> `storage_service.delete` không được gọi.
  - `test_concurrent_intake_integrity_error_no_winner_calls_compensation_delete`: `IntegrityError` nhưng không có winner -> compensation delete được gọi.
  - `test_concurrent_intake_corrupted_winner_revision_raises_app_exception`: Winner không có revision hợp lệ -> ném HTTP 409 `DOCUMENT_REVISION_INVALID`.
  - `test_concurrent_intake_winner_membership_not_duplicated`: Membership của winner không bị tạo trùng khi đã thuộc nhóm.

---

### 1.2. Giữ Ổn Định Idempotency-Key Khi Người Dùng Retry (Vấn đề 2)
- **Files**:
  - `frontend/src/features/documents/utils/idempotency.ts`
  - `frontend/src/features/documents/utils/idempotency.test.ts`
  - `frontend/src/features/documents/components/document-upload-modal.tsx`
- **Hiện tượng cũ**: UUID được tạo mới bên trong mỗi lần chạy `handleBatchUpload`. Nếu server đã nhận request nhưng mạng frontend chập chờn, người dùng bấm nút tải lên lần hai sẽ gửi UUID mới, phá vỡ cơ chế Idempotent Retry.
- **Giải pháp triệt để**:
  1. Xây dựng module độc lập `FileIdempotencyManager` sử dụng `WeakMap<File, string>`.
  2. Cung cấp helper duy nhất `getOrCreate(file: File): string`:
     - Nếu đối tượng `File` đã có key trong bộ nhớ thì trả về đúng UUID đó.
     - Nếu chưa có thì khởi tạo `crypto.randomUUID()` mới.
     - Cùng một file trong modal và cùng một phiên retry luôn nhận cùng một key.
     - Khi reset form hoặc đóng modal (`reset()`), khởi tạo lại WeakMap để phiên mới nhận key mới.
     - Không lưu UUID bằng tên file đơn thuần để tránh va chạm khi hai file khác nhau trùng tên.
  3. Tích hợp vào `DocumentUploadModal`:
     - Sử dụng `idempotencyKeysRef = useRef<FileIdempotencyManager>(new FileIdempotencyManager())`.
     - Trong `handleBatchUpload`, lấy key qua `idempotencyKeysRef.current.getOrCreate(file)`.
     - Gọi `idempotencyKeysRef.current.reset()` trong `resetForm()` khi modal đóng hoặc hủy.
     - Tiếp tục truyền key qua header `Idempotency-Key` của `documentsApi.intakeDocument`, không đưa vào `FormData`.
- **Unit tests**:
  - `idempotency.test.ts` bao phủ 100% 3 kịch bản:
    1. Cùng một file gọi nhiều lần trả cùng key (stable retry).
    2. Hai file khác nhau trả hai key riêng biệt.
    3. Sau khi reset, file được cấp key mới.

---

### 1.3. Chuyển Toàn Bộ Endpoint Legacy V1 Sang Intake V2 (Vấn đề 3)
- **Files**:
  - `backend/app/modules/documents/router.py`
  - `backend/app/modules/documents/service.py`
  - `frontend/src/services/documents-api.ts`
- **Hiện tượng cũ**: Endpoint deprecated `POST /documents/upload` chỉ gọi Intake V2 khi có `group_id`; nếu không có `group_id`, nó vẫn chạy pipeline upload/parse đồng bộ cũ.
- **Giải pháp triệt để**:
  1. Mọi request gửi tới `POST /documents/upload` (dù có hay không có `group_id`) đều đi qua orchestration bất đồng bộ `document_intake_service.intake_document(...)`.
  2. Tiếp nhận header `Idempotency-Key` qua FastAPI `Header(None, alias="Idempotency-Key")` và chuyển tiếp nguyên vẹn sang `intake_document`.
  3. Truyền đầy đủ: `actor`, `tenant_id`, `workspace_id`, `group_id`, metadata NĐ 30, và `idempotency_key`.
  4. Sau khi Intake V2 tiếp nhận tài liệu (HTTP 202 Accepted), sử dụng `document_repository_service.get_document(db, intake_res.document_id, actor)` để chuyển đổi sang `RepositoryDocumentResponse`, giữ tương thích 100% cho các client cũ.
  5. Tuyệt đối không gọi `document_repository_service.upload_document(...)` từ router legacy nữa.
  6. Tham số `auto_parse` chỉ giữ lại trong schema để tương thích client cũ (đánh dấu deprecated); không kích hoạt pipeline đồng bộ.
  7. Frontend `documents-api.ts` hỗ trợ tùy chọn truyền `idempotency_key` và header `Idempotency-Key` cho hàm `uploadDocument`.
- **Regression tests**:
  - `test_legacy_v1_upload_always_routes_to_intake_v2_with_and_without_group`: Kiểm tra cả 2 luồng có `group_id` và không có `group_id` đều đi qua `intake_document`, chuyển tiếp `Idempotency-Key`, không gọi `upload_document`, và trả đúng `RepositoryDocumentResponse`.

---

### 1.4. Không Báo "Xuất Bản Hoàn Tất" Khi Mới Chỉ Tạo Binding (Vấn đề 4)
- **File**: `frontend/src/features/documents/components/attach-group-to-knowledge-dialog.tsx`
- **Hiện tượng cũ**: Request gửi `auto_activate: false` nhưng giao diện lại hiển thị "Đưa Vào Kho Tri Thức Hoàn Tất", "Đã xử lý xuất bản tài liệu", toast "Đã đưa kho tài liệu vào Kho Tri Thức thành công" dù chưa lập chỉ mục (index) và chưa kích hoạt RAG.
- **Giải pháp triệt để**:
  1. Giữ nguyên `auto_activate: false`.
  2. Chuẩn hóa ngữ nghĩa hiển thị trung thực:
     - Tiêu đề thành công: `Đã gắn nguồn tài liệu`.
     - Mô tả chi tiết: `Các tài liệu sẵn sàng đã được liên kết với Kho tri thức. Chúng cần được lập chỉ mục trước khi có thể dùng để truy xuất RAG.`
     - Toast thông báo: `Đã gắn ${createdCount} tài liệu vào Kho tri thức.`
     - Loại bỏ triệt để các cụm từ "xuất bản hoàn tất", "sẵn sàng sử dụng", "đã lập chỉ mục" khi response chưa có `index_revision_id`.
  3. Nút hành động cuối dialog đổi thành `Mở Kho tri thức` (dẫn tới trang chi tiết kho `/knowledge/collections/:id` để cán bộ tiếp tục thực hiện: Gắn nguồn -> Lập chỉ mục -> Kiểm tra chất lượng -> Kích hoạt).
  4. Xử lý trạng thái lỗi tải danh sách Kho tri thức (`isCollectionsError`):
     - Hiển thị banner lỗi trang nhã kèm icon `AlertCircle` và nút `Thử lại` gọi `refetchCollections()`.
     - Ngăn chặn triệt để việc render Select rỗng gây hiểu nhầm hệ thống không có dữ liệu.

---

## 2. Kết Quả Kiểm Thử (Quality Gate)

### 2.1. Backend Ruff Linter
```bash
uv run ruff check .
# All checks passed! (0 errors)
```

### 2.2. Backend Document Workflow Suites (Pytest)
```bash
uv run --extra dev pytest -v tests/test_document_repository_workflow.py tests/test_document_groups_and_knowledge_attach.py tests/test_document_revisions_lifecycle.py
# 45/45 PASSED (100%) in 26.13s
```
*Tất cả 5 test cases regression mới đều vượt qua 100%.*

### 2.3. Frontend Unit Tests (Bun Test)
```bash
bun test src/features/documents/utils/idempotency.test.ts
# 3 pass, 0 fail (100%)
```

### 2.4. Frontend Biome Linter
```bash
bun x biome check src/features/documents src/services/documents-api.ts
# Checked 13 files in 36ms. No fixes applied. (0 errors)
```

### 2.5. Frontend Production Build
```bash
bun run build
# ✓ built in 3.20s (0 TypeScript errors, 0 compilation warnings)
```

### 2.6. Kiểm Tra Toàn Bộ Suite Backend & Đối Soát Lỗi Nền
Toàn bộ các test cases thuộc phạm vi tài liệu, nhóm tài liệu, revision và intake đều đạt 100%. Các lỗi nền ngoài phạm vi xuất hiện trong lần chạy toàn bộ hệ thống đều liên quan tới các dịch vụ bên ngoài (như Qdrant vector database offline hoặc AI server vLLM on-premise không có kết nối trong môi trường sandbox), hoàn toàn không phát sinh từ 4 thay đổi của phiên này.

---

## 3. Xác Nhận Tuân Thủ Quy Định

- [x] **Zero changes to `qnu-sso`**: Không có bất kỳ thay đổi nào trong repository `qnu-sso`.
- [x] **Zero runtime artifacts commit**: Thư mục `backend/storage/documents/` không bị đưa vào version control.
- [x] **Zero mock IDs**: Không tạo revision ID giả hay job ID giả.
- [x] **RFC 7807 Error Handling**: Mọi ngoại lệ nghiệp vụ đều dùng `AppException`.
- [x] **Sẵn sàng chuyển giao**: Kho tài liệu đã đạt trạng thái production-ready vững chắc, sẵn sàng 100% để bước sang thiết kế quy trình Kho tri thức.
