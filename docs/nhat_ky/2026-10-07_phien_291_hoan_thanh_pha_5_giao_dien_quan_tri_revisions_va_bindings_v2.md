# NHẬT KÝ LÀM VIỆC — PHIÊN #291
## Hoàn Thành Pha 5 Kế Hoạch 11: Giao Diện Quản Trị Frontend V2 — Quản Lý Chuỗi Phiên Bản Document Revisions & Thẩm Định Quality Gate, Liên Kết Tri Thức Knowledge Bindings & Xuất Bản An Toàn Zero-Downtime

- **Ngày thực hiện**: 2026-10-07
- **Kỹ sư / AI Agent**: Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu phiên**: Hoàn thành toàn diện **Pha 5 (Giao diện Quản trị Frontend V2)** theo [Kế Hoạch 11 (Tiếp nhận một lần — Xuất bản an toàn)](../ke_hoach/11_ke_hoach_trien_khai_quy_trinh_tiep_nhan_mot_lan_xuat_ban_tri_thuc_an_toan.md) và [ADR-011](../kien_truc/ADR-011_kien_truc_tiep_nhan_mot_lan_va_xuat_ban_tri_thuc_an_toan.md).

---

### 1. Bối Cảnh & Mục Tiêu Kỹ Thuật

Sau khi hoàn thành 5 phiên Backend trước đó (Pha 0: ADR-011 & Contracts V2; Pha 1: Schema CSDL; Pha 2: Async Intake & Quality Gate; Pha 3: Knowledge Bindings & Parity Gate; Pha 4: Retrieval Engine V2 & Citations), hệ thống cần một lớp giao diện người dùng hoàn chỉnh, đẳng cấp cao để cán bộ quản trị:
1. **Tại Kho Tài Liệu Tập Trung (`/documents/:id`)**:
   - Theo dõi chuỗi phiên bản bất biến (Audit Trail) của tài liệu (`v1, v2,...`).
   - Quan sát báo cáo kiểm định chất lượng tự động **Quality Gate Report** (Mật độ ký tự, Bảng biểu, Chuẩn hóa font UTF-8, Độ dài tối thiểu, Điểm số đánh giá tự động).
   - Hiệu đính nội dung Markdown trực tiếp với lý do kiểm toán bắt buộc.
   - Phê duyệt thủ công (`Approve -> Ready`) hoặc Từ chối (`Reject`) hoặc Thử lại bóc tách (`Retry`) với tùy chọn OCR Engine.
2. **Tại Kho Tri Thức (`/knowledge/collections/:id`)**:
   - Bổ sung Tab chuyên biệt **"Liên kết V2 (ADR-011)"** (`CollectionBindingsTab`).
   - Liên kết tài liệu từ Kho Trung Tâm (`available-documents`) với chiến lược chunking và sync policy linh hoạt.
   - Dựng chỉ mục Staging độc lập với kiểm tra **Parity Gate** (Vector points vs expected chunks vs FTS lexical records).
   - Kích hoạt nguyên tử **Atomic Pointer Swap** (`promoteIndexRevision`) chuyển dịch truy vấn người dùng mượt mà sang Epoch mới mà không gián đoạn dịch vụ (Zero Downtime).

---

### 2. Các Tệp Mã Nguồn Đã Thay Đổi & Nâng Cấp

1. **`frontend/src/types/documents.ts`**:
   - Mở rộng `RepositoryDocumentListItem` và `RepositoryDocument` với `current_revision_id?: string | null`.
   - Bổ sung `QualityReportCheck`, `QualityReport` (`overall_status`, `overall_score`, `checks`).
   - Bổ sung `DocumentRevisionListItem` (`is_current`, `quality_overall`, `revision_no`, `status`).
   - Bổ sung `DocumentRevision` (`review_notes`, `parsed_markdown`, `quality_report`).
2. **`frontend/src/types/knowledge.ts`**:
   - Bổ sung đầy đủ types V2: `AvailableRepositoryDocumentItem`, `AvailableRepositoryDocumentsResponse`, `BindingSelectionItem`, `CreateKnowledgeBindingsRequest`, `BindingResultItem`, `CreateKnowledgeBindingsResponse`, `KnowledgeBinding`, `KnowledgeIndexRevision`, `BuildStagingIndexRequest`, `IndexActivationRequest`, `IndexActivationResponse`.
3. **`frontend/src/services/documents-api.ts`**:
   - Bổ sung các phương thức gọi API Revisions V2: `getRevisions`, `getRevision`, `updateRevisionContent`, `reviewRevision`, `retryRevision`.
4. **`frontend/src/services/knowledge-api.ts`**:
   - Bổ sung các phương thức gọi API Publishing V2: `getAvailableDocuments`, `createBindings`, `getBindings`, `getBinding`, `detachBinding`, `buildStagingIndex`, `promoteIndexRevision`, `getIndexRevisions`.
5. **`frontend/src/features/documents/document-detail-page.tsx`**:
   - Nâng cấp Tabs 3 cột: "Phiên Bản (Revisions V2)", "Markdown Sạch", "Xem Trước PDF".
   - Bảng lịch sử chuỗi phiên bản bất biến (v1, v2) kèm trạng thái, OCR engine, ngày tạo.
   - Thẻ báo cáo thẩm định tự động Quality Gate Report với điểm % và 4 chỉ số chi tiết.
   - Dialog "Hiệu đính Markdown" (`isEditMarkdownOpen`) có nhập lý do kiểm toán ISO.
   - Dialog "Thẩm định chất lượng" (`isReviewOpen`) phê duyệt chuyển sang trạng thái `ready`.
   - Dialog "Thử lại bóc tách" (`isRetryOpen`) cho phép chọn OCR engine (`PyMuPdfParser` hoặc `DoclingParser`).
6. **`frontend/src/components/knowledge/types.ts`**:
   - Mở rộng union type `CollectionDetailTab`: thêm `"bindings"`.
7. **`frontend/src/components/knowledge/tabs/collection-bindings-tab.tsx` (Tạo mới)**:
   - Module tab độc lập quản lý Knowledge Publishing V2: Bento grid 2 cột (Danh sách Bindings bên trái, Chi tiết Index Revisions & Parity Report bên phải).
   - Dialog liên kết tài liệu từ kho trung tâm (`BindDocumentsDialog`) có ô tìm kiếm, chọn nhiều file, kiểm tra tài liệu đã thẩm định.
   - Thẻ chi tiết Parity Gate: kiểm tra so khớp `vector_count` vs `expected_chunks` vs `lexical_count`.
   - Dialog kích hoạt nguyên tử Atomic Pointer Swap (`promoteIndexRevision`) nhập lý do phát hành.
   - Hủy liên kết tài liệu an toàn (`detachBinding`).
8. **`frontend/src/features/knowledge/collection-detail-page.tsx`**:
   - Tích hợp tab `bindings` (icon `Link2`, nhãn "Liên kết V2 (ADR-011)").

---

### 3. Kết Quả Kiểm Thử & Xác Nhận Chất Lượng

- **Biome Linter**:
  ```bash
  npx @biomejs/biome check --write src/types/documents.ts src/types/knowledge.ts src/services/documents-api.ts src/services/knowledge-api.ts src/features/documents/document-detail-page.tsx src/features/knowledge/collection-detail-page.tsx src/components/knowledge/tabs/collection-bindings-tab.tsx src/components/knowledge/types.ts
  ```
  - **Kết quả**: `Checked 8 files in 51ms. No fixes applied.` (0 lỗi, 0 cảnh báo, 100% code sạch).
- **TypeScript Typecheck & Vite Production Bundle Build**:
  ```bash
  npm run build # (vite build && tsc --noEmit)
  ```
  - **Kết quả**: Hoàn tất thành công 100% trong **4.41s**, **0 lỗi TypeScript, 0 lỗi JSX, exit code 0**.
- **Tuân thủ quy tắc kiến trúc (AGENTS.md & `qnu-frontend-architect`)**:
  - Academic Teal OKLCH design tokens.
  - Zero Emoji: Sử dụng 100% icon Lucide (`Link2`, `History`, `Layers`, `ArrowRightLeft`, `ShieldCheck`, `CheckCircle2`, `AlertTriangle`).
  - Tái sử dụng tối đa Radix UI Primitives (`Table`, `Badge`, `Button`, `Dialog`, `Textarea`, `Tabs`, `Card`).
  - Semantic a11y: Dùng thẻ `<button type="button">` tương tác, có `disabled` state rõ ràng.

---

### 4. Kết Luận & Kế Hoạch Tiếp Theo

Pha 5 (Giao diện Quản trị Frontend V2) đã hoàn thành xuất sắc, đưa toàn bộ quy trình **"Tiếp nhận một lần — Xuất bản an toàn"** từ hạ tầng backend lên giao diện đồ họa trực quan, tiện dụng cho cán bộ nhà trường.
Sẵn sàng cho **Phiên 7 (Pha 6: Testing Tích Hợp End-to-End, Canary Deployment & Tài Liệu Vận Hành)** theo Kế hoạch 11.
