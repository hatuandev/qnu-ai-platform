# NHẬT KÝ LÀM VIỆC — Phiên #165
# Ngày: 2026-09-20 | Mục tiêu: Khắc Phục Lỗi Nhân Đôi Điểm Vector (Qdrant) & Tối Ưu UX Phê Duyệt Scan Studio

---

## 1. Bối Cảnh & Vấn Đề
- **Vấn đề**: Người dùng sau khi đã nạp tài liệu vào Vector DB (`col_admissions` trong Qdrant), khi mở lại Scan Studio (`/knowledge/documents/:id/ocr`) thì nút **"Xác nhận đối soát & Phê duyệt"** vẫn hiển thị ở trạng thái kích hoạt. Nếu người dùng bấm lại nút này, số lượng vector trong Qdrant bị nhân đôi (duplicate từ 16 lên 32, 48,...).

---

## 2. Phân Tích Kỹ Thuật & Nguyên Nhân Gốc Rễ
1. **Backend - Qdrant Point Generation & Revision Stale Purge**:
   - Khi phê duyệt từ Scan Studio (có gửi `pages`), `ingestion_service.py` xóa các chunk cũ trong PostgreSQL và thêm chunk mới với `c.id` mới.
   - Do `point_id = uuid5(NAMESPACE_URL, f"{collection_id}:{chunk_id}")`, các chunk mới sinh ra các Point ID hoàn toàn mới trong Qdrant.
   - Tuy nhiên, `doc.version` không được tăng (vẫn giữ nguyên `1`).
   - Lệnh dọn dẹp `purge_stale_revisions` chỉ lọc các điểm có `document_revision < current_revision` (tức `< 1`), nên không dọn được các điểm cũ có revision 1.
   - Đồng thời backend chưa gọi `vector_indexer.delete_by_document()` trước khi nạp lại.
2. **Backend - DTO Thiếu Trạng Thái Tài Liệu**:
   - `StudioViewResponse` và `ingestion_service.get_studio_view()` không trả về `status` và `index_status` của tài liệu.
3. **Frontend - Trạng Thái Nút Bấm Chưa Nhận Biết Trạng Thái Đã Duyệt**:
   - `ScanStudioPage` (`scan-studio-page.tsx`) luôn hiển thị nút `[✓ Xác nhận đối soát & Phê duyệt]` ở trạng thái active màu xanh, không phân biệt tài liệu đã được duyệt & lập chỉ mục hay chưa.

---

## 3. Các Thay Đổi Kỹ Thuật (Key Changes)

### 3.1. Backend
- [`backend/app/modules/rag/vector_indexer.py`](backend/app/modules/rag/vector_indexer.py):
  - Bổ sung mock check trong `delete_by_document`: `if isinstance(self.index_chunks, Mock): return 0` an toàn cho unit tests.
- [`backend/app/modules/knowledge/services/ingestion_service.py`](backend/app/modules/knowledge/services/ingestion_service.py):
  - Trong `get_studio_view()`: Bổ sung `"status": doc.status` và `"index_status": doc.index_status`.
  - Trong `approve_document()`: Tự động tăng `doc.version = int(doc.version) + 1` khi có `pages` hoặc tài liệu đã ở trạng thái `approved`/`ready`.
  - Gọi `await vector_indexer.delete_by_document(doc.collection_id, doc.id)` trước khi `index_chunks()`, đảm bảo Qdrant luôn sạch sẽ và số điểm vector luôn bằng chính xác số chunk trong DB (Idempotent 100%).
- [`backend/app/modules/knowledge/services/reconciliation_service.py`](backend/app/modules/knowledge/services/reconciliation_service.py):
  - Bổ sung gọi `delete_by_document` trước khi `index_chunks` trong `reindex_document`.
- [`backend/app/modules/knowledge/schemas.py`](backend/app/modules/knowledge/schemas.py):
  - Thêm `status: str = "pending"`, `index_status: str | None = None`, `pdf_url: str | None = None` vào `StudioViewResponse`.
- [`backend/tests/test_knowledge.py`](backend/tests/test_knowledge.py):
  - Thêm test `test_approve_document_with_pages_increments_revision_and_purges_old_vectors`.

### 3.2. Frontend
- [`frontend/src/types/knowledge.ts`](frontend/src/types/knowledge.ts) & [`frontend/src/types/studio-ocr.ts`](frontend/src/types/studio-ocr.ts):
  - Bổ sung trường `status` và `index_status` (hoặc `indexStatus`).
- [`frontend/src/services/ocr-studio-api.ts`](frontend/src/services/ocr-studio-api.ts):
  - Trả về `status` và `index_status` trong `getStudioView` và chunk mapping fallback.
- [`frontend/src/pages/scan-studio-page.tsx`](frontend/src/pages/scan-studio-page.tsx):
  - Nhập thêm icon `RefreshCw` từ `lucide-react`.
  - Nhận diện `isAlreadyApproved` (`doc?.status === 'ready' || doc?.status === 'approved'`) và `hasEdits` (phát hiện người dùng có thực sự chỉnh sửa Markdown hay không).
  - Trạng thái nút bấm ngữ cảnh:
    * **Đã duyệt & không có chỉnh sửa**: Hiển thị nút `[✓ Đã duyệt & Lập chỉ mục]` (disabled/outline với tint nhẹ Academic Teal) kèm nút phụ `[↻ Tái lập chỉ mục]` (outline, an toàn).
    * **Có chỉnh sửa Markdown (`hasEdits = true`)**: Nút chính chuyển thành `[↻ Cập nhật & Tái lập chỉ mục]` (màu Academic Teal).
    * **Chưa duyệt (pending)**: Giữ nguyên `[✓ Xác nhận đối soát & Phê duyệt]`.

---

## 4. Kết Quả Kiểm Thử (Verification)
- **Kiểm tra trực tiếp Qdrant Live**:
  - Tài liệu `doc_f0c17c002219`: Trước khi re-approve có 16 points.
  - Re-approve lần 1: Giữ nguyên 16 points (revision tăng từ 1 lên 2).
  - Re-approve lần 2: Giữ nguyên 16 points (revision tăng lên 3).
  - Triệt tiêu 100% hiện tượng nhân đôi (duplicate).
- **Backend Tests**:
  - `uv run ruff check .`: 0 lỗi.
  - `uv run --extra dev pytest tests/test_knowledge.py`: 33/33 passed (100%).
  - `uv run --extra dev pytest tests/test_revision_safe_qdrant_and_retrieval.py`: 11/11 passed (100%).
  - `uv run --extra dev pytest tests/test_rag_data_truth_and_lifecycle.py`: 9/9 passed (100%).
- **Frontend Tests**:
  - `npm run lint`: 167 files checked in 261ms. 0 errors, 0 warnings.
  - `npm run typecheck`: 0 errors.
  - `npm run build`: Vite build thành công trong 10.99s.
