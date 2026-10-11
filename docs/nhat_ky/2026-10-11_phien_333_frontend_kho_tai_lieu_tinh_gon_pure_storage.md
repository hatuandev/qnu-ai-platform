# NHẬT KÝ LÀM VIỆC — PHIÊN #333
## Dự Án: QNU.AI Platform — Trường Đại Học Quy Nhơn
**Ngày thực hiện**: 2026-10-11  
**Vai trò**: Senior Full-Stack Architect & Enterprise AI Systems Specialist  
**Mục tiêu**: Thực Hiện Phiên 6 Kế Hoạch 12 — Frontend Kho Tài Liệu Tinh Gọn (Pure Storage UI / Document Vault), Tách Triệt Để Khỏi Parsing & Knowledge Theo Chuẩn ADR-012

---

### 1. Bối Cảnh & Yêu Cầu Kỹ Thuật (Phiên 6 / Kế Hoạch 12)
- Theo kiến trúc phân rã **ADR-012** và kế hoạch 8 phiên tại `docs/ke_hoach/12_ke_hoach_tach_kho_tai_lieu_va_nap_tri_thuc_da_embedding.md`:
  - Kho tài liệu (`/documents`) đóng vai trò là **Kho Lưu Trữ Tệp Thuần Túy** (*Storage Repository / Document Vault*) chịu trách nhiệm lưu trữ an toàn tệp gốc (MinIO S3), xác thực mã băm SHA-256 chống trùng lặp, quản lý phân loại nhóm tệp (`DocumentGroup`) và lịch sử phiên bản tệp gốc (`RepositoryFileRevision`).
  - Toàn bộ tác vụ trí tuệ tài liệu (Bóc tách OCR, sinh Markdown, Quality Gate, duyệt/từ chối, reparse, phân đoạn chunks, multi-embedding) đã được chuyển giao hoàn toàn sang domain Knowledge (`/knowledge`).
  - Do đó, giao diện Frontend Kho tài liệu cần được tái thiết kế tinh gọn:
    1. **Loại bỏ 100% UI bóc tách khỏi Kho tài liệu**: Gỡ bỏ các dialogs/buttons/actions liên quan đến parsing: Reparse Markdown modal, Quality Gate checklist, Approve/Reject review drawer, Canonical Markdown editor, Retry parse.
    2. **Loại bỏ luồng đẩy một chiều cũ sang Kho tri thức**: Xóa bỏ hoàn toàn dialog `AttachGroupToKnowledgeDialog` và nút "Đưa vào kho tri thức" trong chi tiết nhóm. Việc nạp tài liệu được thực hiện chủ động từ Kho tri thức (`/knowledge/:collectionId/add-documents`).
    3. **Tái thiết kế trang chi tiết tài liệu (`DocumentDetailPage`) thành 3 tabs thuần Storage**:
       - `preview`: Trình xem trước tệp tài liệu gốc qua file viewer.
       - `info`: Thuộc tính metadata lưu trữ (kích thước tệp, loại MIME, SHA-256 hash, nhóm trực thuộc, ngày tải).
       - `history`: Lịch sử các phiên bản tệp gốc (`RepositoryFileRevision`) qua endpoint `GET /documents/{id}/file-revisions`.
    4. **Cập nhật KPI Metrics & Bảng biểu theo Storage Domain**:
       - KPIs chuyển sang quản lý lưu trữ: "Tổng Tài Liệu", "Dung Lượng Lưu Trữ", "Kho Lưu Trữ Trực Thuộc", "Kho Đang Chứa Tệp".
       - Bỏ cột "Trạng Thái MD", "Kho Tri Thức"; bổ sung cột "Kho Lưu Trữ Trực Thuộc", "Dung Lượng" và "Mã Băm SHA-256".
    5. **Cập nhật Microcopy chuẩn Kế hoạch 12**:
       - Upload modal: *"Tệp được lưu an toàn trong Kho tài liệu. Việc bóc tách và lập chỉ mục được thực hiện khi bạn nạp tệp vào Kho tri thức."*

---

### 2. Các Tệp Đã Thay Đổi & Tạo Mới

1. **Backend Service & Router (`backend/app/modules/documents/`)**:
   - `backend/app/modules/documents/service.py`:
     - Bổ sung `list_file_revisions(db, tenant_id, document_id)`: Truy vấn an toàn bảng `RepositoryFileRevision`, sắp xếp theo `revision_number desc`.
   - `backend/app/modules/documents/router.py`:
     - Thêm endpoint `GET /documents/{document_id}/file-revisions` trả về `RepositoryFileRevisionResponse` cho giao diện lịch sử tệp gốc.

2. **Frontend Types & Services (`frontend/src/`)**:
   - `frontend/src/types/documents.ts`:
     - Bổ sung `RepositoryFileRevisionItem`, `RepositoryFileRevisionResponse`.
     - Mở rộng `DocumentStats` hỗ trợ `total_groups_count`, `active_groups_count`.
   - `frontend/src/services/documents-api.ts`:
     - Bổ sung API client method `getFileRevisions(documentId: string)`.

3. **Frontend Pages & Components Refactored**:
   - `frontend/src/features/documents/document-detail-page.tsx`:
     - Tinh gọn thành 3 tab: `preview`, `info`, `history`.
     - Tab `history` đọc dữ liệu từ `documentsApi.getFileRevisions`.
     - Xóa 100% dialogs liên quan parsing (reparse, review, quality gate, markdown viewer/editor).
   - `frontend/src/features/documents/documents-page.tsx`:
     - Cập nhật 4 KPIs Storage: "Tổng Tài Liệu", "Dung Lượng Lưu Trữ", "Định Dạng Tệp", "Kho Trực Thuộc".
     - Loại bỏ bộ lọc `parseStatus` và action `reparseMutation`.
   - `frontend/src/features/documents/components/document-card.tsx`:
     - Xóa `onReparse`, xóa parse status badges, xóa action "Bóc Tách Lại MD", hiển thị kích thước và mã băm SHA-256.
   - `frontend/src/features/documents/components/documents-table.tsx`:
     - Xóa cột "Trạng Thái MD" và "Kho Tri Thức". Thay bằng cột "Kho Lưu Trữ Trực Thuộc", "Dung Lượng", "Ngày Tải".
   - `frontend/src/features/documents/components/document-upload-modal.tsx`:
     - Cập nhật microcopy chuẩn ADR-012, hỗ trợ status `"stored"`, loại bỏ thông báo bóc tách tự động.
   - `frontend/src/features/documents/document-group-detail-page.tsx`:
     - Xóa nút "Đưa vào kho tri thức" (`AttachGroupToKnowledgeDialog`), cập nhật KPI Storage domain, xóa bộ lọc parse status.
   - `frontend/src/features/documents/document-groups-page.tsx`:
     - Cập nhật PageHeader description lưu trữ S3, cập nhật 4 KPI Metrics ("Tổng Kho Tài Liệu", "Tổng Tài Liệu Trực Thuộc", "Kho Đang Chứa Tệp", "Kho Chưa Có Tệp"), xóa các status parse cũ (`ready_documents`, `processing_documents`).
   - `frontend/src/features/documents/components/select-documents-for-group-modal.tsx`:
     - Cập nhật cột bảng từ "Trạng Thái MD" sang "Dung Lượng" (`formatFileSize(doc.file_size_bytes)`).
   - **Xóa bỏ file mồ côi**:
     - `frontend/src/features/documents/components/attach-group-to-knowledge-dialog.tsx` (loại bỏ hoàn toàn luồng đẩy sang Kho tri thức).

---

### 3. Kết Quả Kiểm Thử & Quality Gate

1. **Backend**:
   - `uv run ruff check .`: **All checks passed!** (0 cảnh báo, 0 lỗi linter).
   - `uv run --extra dev pytest tests/test_document_repository_workflow.py -v`: **29/29 tests passed** (100%).
   - `uv run --extra dev pytest tests/test_document_repository.py -v`: **6/6 tests passed** (100%).

2. **Frontend**:
   - `npm run build` (`vite build && tsc --noEmit`): **Exit code 0** (0 lỗi TypeScript, 0 lỗi cú pháp, bundle hoàn tất trong 2.93s).

---

### 4. Bài Học Rút Ra & Điểm Cần Lưu Ý
- **Phân rã trách nhiệm rõ ràng (Single Responsibility / Separation of Concerns)**: Việc tách Kho tài liệu thành Document Vault giúp UI trở nên sạch sẽ, tốc độ phản hồi nhanh, không còn tình trạng tải trùng trạng thái parse phức tạp khi người dùng chỉ muốn lưu trữ hoặc phân loại file.
- **Microcopy phản ánh chính xác kiến trúc**: Người dùng hiểu rõ quy trình: File tải lên Kho tài liệu -> Được lưu an toàn MinIO S3 & băm SHA-256 -> Khi nào cần RAG thì vào Kho tri thức nạp vào (Parse once, Chunk once, Embed many).
- Sẵn sàng tiến hành **Phiên 7 Kế Hoạch 12**: Tích hợp luồng nạp tri thức đầu-cuối từ UI Kho tri thức (`/knowledge/:collectionId/add-documents`).
