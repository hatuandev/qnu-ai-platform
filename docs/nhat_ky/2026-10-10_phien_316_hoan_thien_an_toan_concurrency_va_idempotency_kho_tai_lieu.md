# Nhật Ký Phiên #316: Hoàn Thiện An Toàn Concurrency & Idempotency Kho Tài Liệu

- **Thời gian**: 2026-10-10 13:35 (UTC+7)
- **Người thực hiện**: Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu**: Xử lý dứt điểm 3 vấn đề kỹ thuật còn lại trong quy trình upload Kho tài liệu:
  1. Tránh để lại object mồ côi trên MinIO khi upload đồng thời cùng nội dung nhưng khác tên file.
  2. Không tạo membership vào nhóm nếu tài liệu winner không có revision hợp lệ.
  3. Thống nhất implementation frontend idempotency với class `FileIdempotencyManager` đã kiểm thử.
- **Ranh giới tuân thủ**:
  - Không sửa repository `qnu-sso`.
  - Không commit file runtime trong `backend/storage/documents/`.
  - Không tạo mock/fallback giả trong production.
  - Zero `any`, zero dead code, chuẩn hóa UTF-8 NFC sạch.

---

## 1. Chi Tiết Các Giải Pháp Kỹ Thuật

### 1.1. Phân Biệt Storage Key Winner và Loser (Mục 1)
- **File**: `backend/app/modules/documents/intake_service.py`
- **Nguyên nhân**: `storage_key` được đặt theo mẫu:
  ```text
  documents/{tenant_id}/{workspace_id}/originals/{file_hash}/{safe_name}
  ```
  Nếu hai request upload cùng nội dung binary (cùng `file_hash`) nhưng khác tên file (khác `safe_name`), hai object riêng biệt sẽ được lưu lên MinIO S3. Khi request thua cuộc gặp `IntegrityError`, nếu chỉ giữ lại object mà không kiểm tra tên file thì object của request thua sẽ bị mồ côi vĩnh viễn trên MinIO.
- **Thuật toán xử lý**:
  - Trong nhánh `except IntegrityError`, sau khi rollback transaction và truy vấn `winner_doc`:
    - **Nếu `winner_doc.storage_path == storage_key`**: Hai request cùng tên file và cùng trỏ vào một object MinIO -> **Tuyệt đối không xóa** vì winner đang sử dụng chính object đó.
    - **Nếu `winner_doc.storage_path != storage_key`**: `storage_key` là object riêng biệt của request thua cuộc -> **Thực hiện xóa đúng `storage_key` của loser** qua `await storage_service.delete(storage_key)` để dọn dẹp object mồ côi, và **tuyệt đối không xóa `winner_doc.storage_path`**.
  - Nếu không tìm thấy winner (transaction thất bại hoàn toàn): Thực hiện compensation-delete `storage_key` và ném lại exception ban đầu.

### 1.2. Chuẩn Hóa Thứ Tự Transaction, Revision & Membership (Mục 2)
- **File**: `backend/app/modules/documents/intake_service.py`
- **Nguyên nhân**: Trước đây, trong nhánh recovery của `IntegrityError`, code thêm `DocumentGroupMembership` vào DB trước khi đối soát tính hợp lệ của revision. Nếu revision bị hỏng (`status not in VALID_REVISION_STATUSES`), hệ thống ném `DOCUMENT_REVISION_INVALID` nhưng membership đã bị commit vào CSDL.
- **Thứ tự thực thi bắt buộc mới**:
  1. `await db.rollback()` giải phóng trạng thái aborted transaction.
  2. Truy vấn `winner_doc` theo `(tenant_id, workspace_id, file_hash, is_active=True)`.
  3. Dọn dẹp `storage_key` của loser nếu `winner_doc.storage_path != storage_key`.
  4. Đọc và xác thực revision thật:
     - Ưu tiên `winner_doc.current_revision`.
     - Nếu chưa nạp, đọc qua `winner_doc.current_revision_id`.
     - Nếu vẫn không có, query `DocumentRevision` mới nhất theo `revision_no.desc()`.
  5. **Kiểm tra hợp lệ**: `winner_rev.status in VALID_REVISION_STATUSES`:
     - Nếu thiếu hoặc không hợp lệ -> ném ngay RFC 7807 `AppException(status_code=409, code="DOCUMENT_REVISION_INVALID")`.
     - **Không tạo `DocumentGroupMembership`**, không cập nhật `group.updated_at`, không commit bất kỳ dữ liệu nào.
  6. **Chỉ khi revision hợp lệ**:
     - Nếu có `group_id`, kiểm tra `DocumentGroupMembership` đã tồn tại chưa.
     - Nếu chưa có, thêm membership, cập nhật `group.updated_at` và commit an toàn.
     - Bọc trong `try ... except IntegrityError`: nếu hai request đồng thời cùng thêm membership, nhánh except sẽ `await db.rollback()` và bỏ qua lỗi duplicate một cách idempotent.
  7. Trả response từ revision thật và JobRecord thật, không sinh ID giả.

### 1.3. Thống Nhất Frontend Idempotency Implementation (Mục 3)
- **Files**:
  - `frontend/src/features/documents/components/document-upload-modal.tsx`
  - `frontend/src/features/documents/utils/idempotency.ts`
  - `frontend/src/features/documents/utils/idempotency.test.ts`
  - `frontend/package.json`
- **Nguyên nhân**: Trước đây `document-upload-modal.tsx` tự cài đặt một `WeakMap` cục bộ, trong khi `idempotency.ts` đã xây dựng class `FileIdempotencyManager`. Điều này tạo ra hai implementation song song.
- **Giải pháp**:
  1. Import trực tiếp `FileIdempotencyManager` từ `../utils/idempotency` vào `document-upload-modal.tsx`.
  2. Sử dụng `idempotencyManagerRef = useRef<FileIdempotencyManager>(new FileIdempotencyManager())`.
  3. Xóa bỏ hoàn toàn `WeakMap` cục bộ và hàm `getOrCreateIdempotencyKey` cục bộ.
  4. Khi upload: gọi `idempotencyManagerRef.current.getOrCreate(file)`. Cùng đối tượng `File` khi retry nhận đúng UUID cũ; các file khác nhau nhận UUID riêng biệt.
  5. Khi đóng modal hoặc reset form (`resetForm()`): gọi `idempotencyManagerRef.current.reset()`. Không reset trong lúc chỉ retry upload lỗi.
  6. Thêm script `"test:documents": "bun test src/features/documents/utils/idempotency.test.ts"` vào `frontend/package.json`.

---

## 2. Kết Quả Kiểm Thử (Quality Gate)

### 2.1. Backend Targeted Suites (Pytest)
```bash
.venv\Scripts\python.exe -m pytest -v tests/test_document_repository_workflow.py tests/test_document_groups_and_knowledge_attach.py tests/test_document_revisions_lifecycle.py
# 47 passed, 1 warning in 26.88s (100%)
```
Toàn bộ 6 regression tests phục vụ 3 vấn đề đều đạt kết quả PASSED:
1. `test_concurrent_intake_winner_exists_does_not_delete_storage_object`: Cùng hash + cùng storage path -> không gọi `storage_service.delete`.
2. `test_concurrent_intake_different_filename_deletes_only_loser_storage_key`: Cùng hash + khác filename -> chỉ xóa `storage_key` của loser, không xóa `winner_doc.storage_path`.
3. `test_concurrent_intake_integrity_error_no_winner_calls_compensation_delete`: IntegrityError không có winner -> compensation delete đúng `storage_key`.
4. `test_concurrent_intake_corrupted_winner_revision_raises_app_exception`: Winner hỏng revision -> ném 409 `DOCUMENT_REVISION_INVALID`, 0 membership được tạo, 0 commit.
5. `test_concurrent_intake_winner_membership_not_duplicated`: Membership đã tồn tại -> không tạo duplicate.
6. `test_concurrent_intake_membership_conflict_handled_idempotently`: 2 request cùng thêm membership -> bắt `IntegrityError`, rollback an toàn và trả kết quả idempotent.

### 2.2. Backend Ruff Linter
```bash
.venv\Scripts\ruff.exe check .
# All checks passed! (0 errors)
```

### 2.3. Frontend Unit Tests (Bun Test)
```bash
bun test src/features/documents/utils/idempotency.test.ts
# 3 pass, 0 fail (100% in 72ms)

bun run test:documents
# 3 pass, 0 fail (100% in 72ms)
```

### 2.4. Frontend Biome Linter
```bash
bun x biome check src/features/documents src/services/documents-api.ts
# Checked 13 files in 43ms. No fixes applied. (0 errors)
```

### 2.5. Frontend Production Bundle Build
```bash
bun run build
# ✓ built in 4.52s (0 TypeScript errors, 0 compilation warnings)
```

---

## 3. Xác Nhận An Toàn & Ranh Giới

- [x] **Không thay đổi `qnu-sso`**: 0 file bị ảnh hưởng.
- [x] **Không commit file runtime**: Thư mục `backend/storage/documents/` không có artifact untracked.
- [x] **Không tạo mock/fake ID**: Trả đúng revision và JobRecord thật từ CSDL.
- [x] **Production modal sử dụng đúng class đã test**: `FileIdempotencyManager` là single source of truth.
